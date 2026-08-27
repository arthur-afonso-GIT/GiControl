import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app import FinanceManager
from backend.infrastructure import JsonFileDataStore


class FinanceManagerCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.data_path = Path(self.temp_dir.name) / "data" / "data.json"
        self.manager = FinanceManager(JsonFileDataStore(self.data_path))

    def add_account(self, balance=1000.0, monthly_income=0.0):
        return self.manager.add_account(
            "Conta principal",
            "Conta Corrente",
            balance,
            monthly_income,
        )

    def add_category(self, category_type="Despesa", monthly_limit=0.0):
        return self.manager.add_category(
            "Categoria de teste",
            category_type,
            monthly_limit,
        )

    def test_initial_storage_contains_default_categories(self):
        self.assertTrue(self.data_path.exists())
        self.assertEqual([], self.manager.get_accounts())
        self.assertEqual([], self.manager.get_transactions())
        self.assertEqual(5, len(self.manager.get_categories()))

    def test_account_changes_are_persisted(self):
        account = self.add_account(balance=250.0, monthly_income=1500.0)

        self.assertTrue(self.manager.update_account_balance(account["id"], 325.5))
        self.assertTrue(self.manager.update_account_monthly_income(account["id"], 1800.0))

        persisted = json.loads(self.data_path.read_text(encoding="utf-8"))
        self.assertEqual(325.5, persisted["accounts"][0]["balance"])
        self.assertEqual(1800.0, persisted["accounts"][0]["monthly_income"])

    def test_category_can_be_created_updated_and_deleted(self):
        category = self.add_category(monthly_limit=500.0)

        updated = self.manager.update_category(
            category["id"],
            "  Mercado  ",
            "Despesa",
            650.0,
        )

        self.assertEqual("Mercado", updated["name"])
        self.assertEqual(650.0, updated["monthly_limit"])
        self.assertTrue(self.manager.delete_category(category["id"]))
        self.assertNotIn(category["id"], [item["id"] for item in self.manager.get_categories()])

    def test_category_with_same_name_and_type_is_updated_instead_of_duplicated(self):
        category = self.manager.add_category("Mercado", "Despesa", 300.0)
        category_count = len(self.manager.get_categories())

        result = self.manager.add_category("  mercado ", "Despesa", 450.0)

        self.assertEqual(category["id"], result["id"])
        self.assertEqual(category_count, len(self.manager.get_categories()))
        self.assertEqual(450.0, result["monthly_limit"])

    def test_income_and_expense_change_balance_and_deletion_reverses_them(self):
        account = self.add_account(balance=1000.0)
        expense_category = self.add_category("Despesa")
        income_category = self.add_category("Receita")

        self.manager.add_transaction(
            200.0, expense_category["id"], account["id"], "Mercado", "Despesa"
        )
        self.manager.add_transaction(
            500.0, income_category["id"], account["id"], "Freelance", "Receita"
        )

        self.assertEqual(1300.0, account["balance"])

        transactions = self.manager.get_transactions()
        expense = next(item for item in transactions if item["type"] == "Despesa")
        income = next(item for item in transactions if item["type"] == "Receita")

        self.assertTrue(self.manager.delete_transaction(expense["id"]))
        self.assertEqual(1500.0, account["balance"])
        self.assertTrue(self.manager.delete_transaction(income["id"]))
        self.assertEqual(1000.0, account["balance"])

    def test_installments_cross_year_and_preserve_total_amount(self):
        account = self.add_account(balance=1000.0)
        category = self.add_category()

        self.manager.add_transaction(
            300.0,
            category["id"],
            account["id"],
            "Compra parcelada",
            "Despesa",
            date="2026-12-31",
            installments=3,
        )

        transactions = self.manager.get_transactions()
        self.assertEqual(["2026-12-31", "2027-01-31", "2027-02-28"], [t["date"] for t in transactions])
        self.assertEqual([" (1/3)", " (2/3)", " (3/3)"], [t["description"][-6:] for t in transactions])
        self.assertAlmostEqual(300.0, sum(t["amount"] for t in transactions))
        self.assertEqual(700.0, account["balance"])

    def test_installments_distribute_remaining_cents_without_changing_total(self):
        account = self.add_account(balance=1000.0)
        category = self.add_category()

        self.manager.add_transaction(
            100.0,
            category["id"],
            account["id"],
            "Compra em três vezes",
            "Despesa",
            date="2026-08-26",
            installments=3,
        )

        amounts = [item["amount"] for item in self.manager.get_transactions()]
        self.assertEqual([33.34, 33.33, 33.33], amounts)
        self.assertEqual(100.0, sum(amounts))
        self.assertEqual(900.0, account["balance"])

    def test_deleting_account_removes_its_transactions(self):
        account = self.add_account()
        category = self.add_category()
        self.manager.add_transaction(
            50.0, category["id"], account["id"], "Despesa", "Despesa"
        )

        self.assertTrue(self.manager.delete_account(account["id"]))
        self.assertEqual([], self.manager.get_accounts())
        self.assertEqual([], self.manager.get_transactions())

    def test_dashboard_uses_greater_of_expected_and_real_income(self):
        account = self.add_account(balance=1000.0, monthly_income=2000.0)
        expense_category = self.add_category("Despesa")
        income_category = self.add_category("Receita")
        current_date = datetime.now().strftime("%Y-%m-%d")

        self.manager.add_transaction(
            500.0,
            expense_category["id"],
            account["id"],
            "Mercado",
            "Despesa",
            date=current_date,
        )
        self.manager.add_transaction(
            1200.0,
            income_category["id"],
            account["id"],
            "Receita",
            "Receita",
            date=current_date,
        )

        metrics = self.manager.get_dashboard_metrics()

        self.assertEqual(1700.0, metrics["current_balance"])
        self.assertEqual(2000.0, metrics["monthly_income"])
        self.assertEqual(500.0, metrics["monthly_expense"])
        self.assertEqual(1500.0, metrics["savings"])
        self.assertEqual(2, len(metrics["recent_transactions"]))


if __name__ == "__main__":
    unittest.main()
