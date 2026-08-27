import unittest
from datetime import date

from backend.application.services import CreateTransactionRequest, TransactionService
from backend.domain import Account, AccountType, Money, TransactionType
from backend.infrastructure import JsonUnitOfWork


class TransactionServiceTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "accounts": [
                {
                    "id": "account",
                    "name": "Conta",
                    "type": "Conta Corrente",
                    "balance": 1000.0,
                    "monthly_income": 0.0,
                }
            ],
            "categories": [],
            "transactions": [],
        }
        self.persist_calls = 0
        self.unit_of_work = JsonUnitOfWork(self.data, self._persist)
        self.service = TransactionService(self.unit_of_work)

    def _persist(self):
        self.persist_calls += 1

    def request(self):
        return CreateTransactionRequest(
            amount=Money.from_value("100"),
            category_id="food",
            account_id="account",
            description="Compra",
            transaction_type=TransactionType.EXPENSE,
            date=date(2026, 12, 31),
            installments=3,
        )

    def test_create_updates_balance_and_transactions_in_one_commit(self):
        transactions = self.service.create(self.request())

        self.assertEqual([33.34, 33.33, 33.33], [float(item.amount.amount) for item in transactions])
        self.assertEqual(["2026-12-31", "2027-01-31", "2027-02-28"], [item["date"] for item in self.data["transactions"]])
        self.assertEqual(900.0, self.data["accounts"][0]["balance"])
        self.assertEqual(1, self.persist_calls)
        self.assertEqual(1, len({item.installment_group_id for item in transactions}))
        self.assertIsNotNone(transactions[0].installment_group_id)
        self.assertEqual([1, 2, 3], [item.installment_number for item in transactions])
        self.assertEqual([3, 3, 3], [item.installment_total for item in transactions])

    def test_delete_reverses_one_installment_in_one_commit(self):
        transactions = self.service.create(self.request())
        self.persist_calls = 0

        self.assertTrue(self.service.delete(transactions[0].id))

        self.assertEqual(933.34, self.data["accounts"][0]["balance"])
        self.assertEqual(2, len(self.data["transactions"]))
        self.assertEqual(1, self.persist_calls)

    def test_delete_installment_series_reverses_full_balance_in_one_commit(self):
        transactions = self.service.create(self.request())
        self.persist_calls = 0

        deleted = self.service.delete_installment_series(transactions[0].installment_group_id)

        self.assertEqual(3, deleted)
        self.assertEqual(1000.0, self.data["accounts"][0]["balance"])
        self.assertEqual([], self.data["transactions"])
        self.assertEqual(1, self.persist_calls)

    def test_delete_missing_installment_series_does_not_persist(self):
        self.assertEqual(0, self.service.delete_installment_series("missing"))
        self.assertEqual(0, self.persist_calls)

    def test_missing_account_rolls_back_without_persisting(self):
        request = CreateTransactionRequest(
            amount=Money.from_value("10"),
            category_id="food",
            account_id="missing",
            description="Compra",
            transaction_type=TransactionType.EXPENSE,
            date=date(2026, 8, 26),
        )

        with self.assertRaises(ValueError):
            self.service.create(request)

        self.assertEqual([], self.data["transactions"])
        self.assertEqual(0, self.persist_calls)


if __name__ == "__main__":
    unittest.main()
