import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.presentation.production import create_production_app


class ProductionAppTests(unittest.TestCase):
    def test_serves_api_and_spa_from_same_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"index.html").write_text("<h1>GiControl</h1>",encoding="utf-8")
            client=TestClient(create_production_app(root))
            self.assertEqual({"status":"ok"},client.get("/api/health").json())
            self.assertIn("GiControl",client.get("/qualquer-rota").text)


if __name__=="__main__":unittest.main()
