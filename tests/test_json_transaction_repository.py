import unittest
from datetime import date

from backend.application.ports import TransactionRepository
from backend.domain import Money, Transaction, TransactionType
from backend.infrastructure.repositories import JsonTransactionRepository


class JsonTransactionRepositoryContractTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "id": "tx-1",
                "amount": 25.5,
                "date": "2026-08-26",
                "category_id": "food",
                "account_id": "main",
                "description": "Mercado",
                "type": "Despesa",
                "is_fixed": False,
            }
        ]
        self.persist_calls = 0
        self.repository = JsonTransactionRepository(self.records, self._persist)

    def _persist(self):
        self.persist_calls += 1

    def make_transaction(self, transaction_id="tx-2", account_id="main"):
        return Transaction(
            id=transaction_id,
            amount=Money.from_value("10.25"),
            date=date(2026, 9, 1),
            category_id="food",
            account_id=account_id,
            description="Teste",
            transaction_type=TransactionType.EXPENSE,
        )

    def test_adapter_satisfies_repository_protocol(self):
        repository: TransactionRepository = self.repository

        self.assertEqual("tx-1", repository.list_all()[0].id)

    def test_maps_legacy_record_to_domain(self):
        transaction = self.repository.get("tx-1")

        self.assertEqual(Money.from_value("25.50"), transaction.amount)
        self.assertEqual(date(2026, 8, 26), transaction.date)
        self.assertEqual(TransactionType.EXPENSE, transaction.transaction_type)

    def test_save_all_persists_batch_once(self):
        transactions = [self.make_transaction("tx-2"), self.make_transaction("tx-3")]

        self.repository.save_all(transactions)

        self.assertEqual(3, len(self.records))
        self.assertEqual(1, self.persist_calls)

    def test_save_updates_existing_record_in_place(self):
        original = self.records[0]
        transaction = Transaction(
            id="tx-1",
            amount=Money.from_value("30"),
            date=date(2026, 8, 27),
            category_id="food",
            account_id="main",
            description="Atualizada",
            transaction_type=TransactionType.EXPENSE,
        )

        self.repository.save(transaction)

        self.assertIs(original, self.records[0])
        self.assertEqual(30.0, original["amount"])
        self.assertEqual(1, self.persist_calls)

    def test_delete_by_account_removes_only_linked_records(self):
        self.repository.save(self.make_transaction("tx-other", "secondary"))
        self.persist_calls = 0

        deleted = self.repository.delete_by_account("main")

        self.assertEqual(1, deleted)
        self.assertEqual(["tx-other"], [record["id"] for record in self.records])
        self.assertEqual(1, self.persist_calls)

    def test_delete_missing_transaction_does_not_persist(self):
        self.assertFalse(self.repository.delete("missing"))
        self.assertEqual(0, self.persist_calls)


if __name__ == "__main__":
    unittest.main()
