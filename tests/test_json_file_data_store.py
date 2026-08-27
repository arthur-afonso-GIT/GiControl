import json
import tempfile
import unittest
from pathlib import Path

from backend.application.ports import DataStore
from backend.infrastructure import JsonFileDataStore


class JsonFileDataStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "nested" / "data.json"
        self.store = JsonFileDataStore(self.path)

    def test_adapter_satisfies_data_store_protocol(self):
        self.assertIsInstance(self.store, DataStore)

    def test_first_load_creates_default_data(self):
        data = self.store.load()

        self.assertTrue(self.path.exists())
        self.assertEqual(5, len(data["categories"]))
        self.assertEqual(data, json.loads(self.path.read_text(encoding="utf-8")))

    def test_save_replaces_file_without_leaving_temporary_files(self):
        data = {"accounts": [{"id": "1"}], "categories": [], "transactions": []}

        self.store.save(data)

        self.assertEqual(data, self.store.load())
        self.assertEqual([self.path], list(self.path.parent.iterdir()))

    def test_invalid_json_returns_empty_legacy_structure(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("invalid", encoding="utf-8")

        self.assertEqual(
            {"accounts": [], "categories": [], "transactions": []},
            self.store.load(),
        )
