import tempfile
import unittest
from pathlib import Path

from backend.infrastructure import (
    JsonFileDataStore,
    SqliteDataStore,
    migrate_data,
)


class DataMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.source = JsonFileDataStore(root / "data.json")
        self.target = SqliteDataStore(root / "fincontrol.db")

    @staticmethod
    def _data(account_id="account-1"):
        return {
            "accounts": [{
                "id": account_id,
                "name": "Principal",
                "type": "Conta Corrente",
                "balance": 500.0,
                "monthly_income": 1000.0,
            }],
            "categories": [],
            "transactions": [],
        }

    def test_migration_copies_and_verifies_json_into_sqlite(self):
        self.source.save(self._data())

        result = migrate_data(self.source, self.target)

        self.assertEqual(1, result.accounts)
        self.assertEqual(0, result.categories)
        self.assertEqual(self.source.load(), self.target.load())

    def test_migration_refuses_to_overwrite_populated_target(self):
        self.source.save(self._data("source"))
        self.target.save(self._data("target"))

        with self.assertRaisesRegex(ValueError, "destino já contém dados"):
            migrate_data(self.source, self.target)

        self.assertEqual("target", self.target.load()["accounts"][0]["id"])

    def test_explicit_overwrite_replaces_target(self):
        self.source.save(self._data("source"))
        self.target.save(self._data("target"))

        migrate_data(self.source, self.target, overwrite=True)

        self.assertEqual("source", self.target.load()["accounts"][0]["id"])
