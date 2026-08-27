import json
import os
import tempfile
from pathlib import Path

from backend.infrastructure.default_data import default_data



class JsonFileDataStore:
    """Adaptador do arquivo JSON legado, isolado da fachada e dos casos de uso."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path).resolve()

    def load(self) -> dict:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            initial_data = default_data()
            self.save(initial_data)
            return initial_data
        try:
            with self.file_path.open("r", encoding="utf-8") as source:
                return json.load(source)
        except json.JSONDecodeError:
            return {"accounts": [], "categories": [], "transactions": []}

    def save(self, data: dict) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.file_path.parent,
                prefix=f".{self.file_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(data, temporary, ensure_ascii=False, indent=4)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.file_path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
