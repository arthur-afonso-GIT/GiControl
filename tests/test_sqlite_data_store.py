import tempfile
import unittest
from pathlib import Path

from app import FinanceManager
from backend.application.ports import DataStore
from backend.infrastructure import SqliteDataStore


class SqliteDataStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "data" / "fincontrol.db"
        self.store = SqliteDataStore(self.path)

    @staticmethod
    def _sample_data():
        return {
            "accounts": [{
                "id": "account-1",
                "name": "Principal",
                "type": "Conta Corrente",
                "balance": 1234.56,
                "monthly_income": 2500.0,
            }],
            "categories": [{
                "id": "category-1",
                "name": "Mercado",
                "type": "Despesa",
                "monthly_limit": 700.25,
            }],
            "transactions": [{
                "id": "transaction-1",
                "amount": 99.99,
                "date": "2026-08-26",
                "category_id": "category-1",
                "account_id": "account-1",
                "description": "Compra",
                "type": "Despesa",
                "is_fixed": False,
            }],
        }

    def test_adapter_satisfies_data_store_protocol(self):
        self.assertIsInstance(self.store, DataStore)

    def test_first_load_creates_schema_and_default_categories(self):
        data = self.store.load()

        self.assertTrue(self.path.exists())
        self.assertEqual(5, len(data["categories"]))

    def test_round_trip_preserves_normalized_financial_data(self):
        expected = self._sample_data()

        self.store.save(expected)

        self.assertEqual(expected, self.store.load())

    def test_failed_save_rolls_back_previous_snapshot(self):
        expected = self._sample_data()
        self.store.save(expected)
        invalid = self._sample_data()
        invalid["transactions"][0].pop("description")

        with self.assertRaises(KeyError):
            self.store.save(invalid)

        self.assertEqual(expected, self.store.load())

    def test_finance_manager_can_restart_using_sqlite(self):
        manager = FinanceManager(self.store)
        account = manager.add_account(
            "SQLite", "Conta Corrente", 250.75, 1200.0
        )

        restarted = FinanceManager(SqliteDataStore(self.path))

        self.assertEqual(account["id"], restarted.get_accounts()[0]["id"])
        self.assertEqual(250.75, restarted.get_accounts()[0]["balance"])

    def test_existing_schema_is_extended_for_installment_series(self):
        self.store.load()
        with self.store._connection() as connection:
            connection.execute("ALTER TABLE transactions RENAME TO transactions_old")
            connection.execute("""CREATE TABLE transactions (
                id TEXT PRIMARY KEY, amount_cents INTEGER NOT NULL, date TEXT NOT NULL,
                category_id TEXT NOT NULL, account_id TEXT NOT NULL,
                description TEXT NOT NULL, type TEXT NOT NULL,
                is_fixed INTEGER NOT NULL DEFAULT 0)""")
            connection.execute("DROP TABLE transactions_old")

        self.store.load()

        with self.store._connection() as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(transactions)")}
        self.assertTrue({"installment_group_id", "installment_number", "installment_total"}.issubset(columns))
