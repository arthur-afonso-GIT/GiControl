import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.infrastructure import (
    JsonFileDataStore,
    PostgresDataStore,
    SqliteDataStore,
    create_default_data_store,
)


class PersistenceBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.data_dir = self.root / "data"
        self.data_dir.mkdir()
        self.json_path = self.data_dir / "data.json"
        self.source_data = {
            "accounts": [{
                "id": "account-1",
                "name": "Principal",
                "type": "Conta Corrente",
                "balance": 100.0,
                "monthly_income": 500.0,
            }],
            "categories": [],
            "transactions": [],
        }
        self.json_path.write_text(
            json.dumps(self.source_data, ensure_ascii=False), encoding="utf-8"
        )

    def test_sqlite_default_migrates_verifies_and_preserves_backup(self):
        store = create_default_data_store(self.root)

        self.assertIsInstance(store, SqliteDataStore)
        self.assertEqual(self.source_data, store.load())
        self.assertEqual(
            self.source_data,
            json.loads(
                (self.data_dir / "data.json.pre-sqlite.bak").read_text(encoding="utf-8")
            ),
        )
        self.assertFalse((self.data_dir / ".fincontrol.migrating.db").exists())

    def test_existing_sqlite_is_reused_without_remigrating_json(self):
        first = create_default_data_store(self.root)
        first.save({"accounts": [], "categories": [], "transactions": []})
        self.json_path.write_text("invalid", encoding="utf-8")

        reused = create_default_data_store(self.root)

        self.assertIsInstance(reused, SqliteDataStore)

    def test_json_mode_keeps_rollback_path_available(self):
        store = create_default_data_store(self.root, mode="json")

        self.assertIsInstance(store, JsonFileDataStore)
        self.assertEqual(self.source_data, store.load())

    def test_invalid_mode_fails_fast(self):
        with self.assertRaisesRegex(ValueError, "sqlite.*json"):
            create_default_data_store(self.root, mode="unknown")

    def test_database_url_selects_postgres_without_opening_connection(self):
        url = "postgresql://user:secret@example.com:5432/gicontrol"
        with patch.dict("os.environ", {"DATABASE_URL": url}, clear=False):
            store = create_default_data_store(self.root)
        self.assertIsInstance(store, PostgresDataStore)
        self.assertEqual(url, store.database_url)

    def test_postgres_mode_requires_database_url(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL"):
                create_default_data_store(self.root, mode="postgres")
