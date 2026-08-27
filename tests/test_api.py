import tempfile
import unittest
from unittest.mock import patch
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from backend.infrastructure import JsonFileDataStore, ServiceContainer
from backend.presentation.api import create_api


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        storage = JsonFileDataStore(Path(self.temp_dir.name) / "data.json")
        self.client = TestClient(create_api(ServiceContainer(storage)))

    def test_health_and_initial_resources(self):
        self.assertEqual({"status": "ok"}, self.client.get("/health").json())
        self.assertEqual([], self.client.get("/accounts").json())
        self.assertEqual(5, len(self.client.get("/categories").json()))

    def test_authentication_can_protect_financial_routes(self):
        with patch.dict("os.environ", {"AUTH_REQUIRED":"true"}):
            self.assertEqual(200, self.client.get("/health").status_code)
            response=self.client.get("/accounts")
            self.assertEqual(401,response.status_code)
            self.assertEqual("Autenticação necessária",response.json()["detail"])

    def test_account_category_transaction_and_dashboard_flow(self):
        account_response = self.client.post("/accounts", json={
            "name": "Conta API",
            "type": "Conta Corrente",
            "initial_balance": 1000,
            "monthly_income": 2000,
        })
        self.assertEqual(201, account_response.status_code)
        account = account_response.json()

        category_response = self.client.post("/categories", json={
            "name": "Mercado",
            "type": "Despesa",
            "monthly_limit": 500,
        })
        self.assertEqual(201, category_response.status_code)
        category = category_response.json()

        transaction_response = self.client.post("/transactions", json={
            "amount": 100,
            "category_id": category["id"],
            "account_id": account["id"],
            "description": "Compra parcelada",
            "type": "Despesa",
            "date": date.today().isoformat(),
            "installments": 3,
        })
        self.assertEqual(201, transaction_response.status_code)
        transactions = transaction_response.json()
        self.assertEqual([33.34, 33.33, 33.33], [item["amount"] for item in transactions])

        accounts = self.client.get("/accounts").json()
        self.assertEqual(900.0, accounts[0]["balance"])
        dashboard = self.client.get("/dashboard").json()
        self.assertEqual(2000.0, dashboard["monthly_income"])
        self.assertEqual(33.34, dashboard["monthly_expense"])
        budgets = self.client.get(f"/budgets?month={date.today():%Y-%m}").json()
        self.assertEqual(1, len(budgets))
        self.assertEqual(33.34, budgets[0]["spent"])

    def test_not_found_and_validation_responses_are_explicit(self):
        missing = self.client.patch(
            "/accounts/missing/balance", json={"value": 10}
        )
        invalid = self.client.post("/transactions", json={
            "amount": 0,
            "category_id": "category",
            "account_id": "account",
            "description": "Inválida",
            "type": "Despesa",
            "date": "2026-08-27",
        })

        self.assertEqual(404, missing.status_code)
        self.assertEqual(422, invalid.status_code)
        self.assertEqual(422, self.client.get("/dashboard?month=08-2026").status_code)
        self.assertEqual(422, self.client.get("/budgets?month=2026-13").status_code)

    def test_dashboard_accepts_reference_month(self):
        account = self.client.post("/accounts", json={
            "name": "Conta API", "type": "Carteira", "initial_balance": 500,
            "monthly_income": 1000,
        }).json()
        category = self.client.get("/categories").json()[0]
        self.client.post("/transactions", json={
            "amount": 240, "category_id": category["id"], "account_id": account["id"],
            "description": "Compra parcelada", "type": "Despesa",
            "date": "2026-08-10", "installments": 2,
        })

        august = self.client.get("/dashboard?month=2026-08").json()
        september = self.client.get("/dashboard?month=2026-09").json()

        self.assertEqual(120, august["monthly_expense"])
        self.assertEqual(120, september["monthly_expense"])

    def test_deleting_transaction_reverses_balance(self):
        account = self.client.post("/accounts", json={
            "name": "Conta API",
            "type": "Carteira",
            "initial_balance": 100,
        }).json()
        transaction = self.client.post("/transactions", json={
            "amount": 25,
            "category_id": "1",
            "account_id": account["id"],
            "description": "Almoço",
            "type": "Despesa",
            "date": "2026-08-27",
        }).json()[0]

        response = self.client.delete(f"/transactions/{transaction['id']}")

        self.assertEqual(204, response.status_code)
        self.assertEqual(100.0, self.client.get("/accounts").json()[0]["balance"])
        self.assertEqual(
            404,
            self.client.delete(f"/transactions/{transaction['id']}").status_code,
        )

    def test_deleting_installment_series_removes_all_occurrences(self):
        account = self.client.post("/accounts", json={"name": "Conta", "type": "Carteira", "initial_balance": 500}).json()
        transactions = self.client.post("/transactions", json={
            "amount": 90, "category_id": "1", "account_id": account["id"],
            "description": "Curso", "type": "Despesa", "date": "2026-08-27", "installments": 3,
        }).json()

        response = self.client.delete(f"/transaction-series/{transactions[0]['installment_group_id']}")

        self.assertEqual(204, response.status_code)
        self.assertEqual([], self.client.get("/transactions").json())
        self.assertEqual(500, self.client.get("/accounts").json()[0]["balance"])

    def test_credit_card_purchase_builds_invoices_without_debiting_account(self):
        account=self.client.post("/accounts",json={"name":"Principal","type":"Conta Corrente","initial_balance":1000}).json()
        card_response=self.client.post("/credit-cards",json={"name":"Roxo","credit_limit":900,"closing_day":20,"due_day":28,"payment_account_id":account["id"]})
        self.assertEqual(201,card_response.status_code);card=card_response.json()
        purchase=self.client.post(f"/credit-cards/{card['id']}/purchases",json={"category_id":"1","description":"Celular","purchase_date":"2026-08-21","total_amount":300,"installments":3})
        self.assertEqual(201,purchase.status_code)
        self.assertEqual([100,100,100],[item["amount"] for item in purchase.json()["installments"]])
        cards=self.client.get("/credit-cards").json()
        self.assertEqual(600,cards[0]["available_limit"])
        invoices=self.client.get(f"/credit-cards/{card['id']}/invoices").json()
        self.assertEqual(3,len(invoices))
        self.assertEqual(1000,self.client.get("/accounts").json()[0]["balance"])
