import os
import shutil
from pathlib import Path

from backend.application.ports import DataStore
from backend.infrastructure.data_migration import migrate_data
from backend.infrastructure.json_file_data_store import JsonFileDataStore
from backend.infrastructure.sqlite_data_store import SqliteDataStore


def create_default_data_store(
    project_dir: str | Path,
    mode: str | None = None,
) -> DataStore:
    """Seleciona a persistência e migra JSON para SQLite antes da ativação."""
    data_dir = Path(project_dir).resolve() / "data"
    json_path = data_dir / "data.json"
    selected_mode = (mode or os.getenv("FINCONTROL_STORAGE", "sqlite")).strip().lower()
    if selected_mode == "json":
        return JsonFileDataStore(json_path)
    if selected_mode != "sqlite":
        raise ValueError("FINCONTROL_STORAGE deve ser 'sqlite' ou 'json'")

    sqlite_path = data_dir / "fincontrol.db"
    if sqlite_path.exists():
        return SqliteDataStore(sqlite_path)

    data_dir.mkdir(parents=True, exist_ok=True)
    source = JsonFileDataStore(json_path)
    backup_path = data_dir / "data.json.pre-sqlite.bak"
    if json_path.exists() and not backup_path.exists():
        shutil.copy2(json_path, backup_path)

    migrating_path = data_dir / ".fincontrol.migrating.db"
    _remove_sqlite_files(migrating_path)
    try:
        target = SqliteDataStore(migrating_path)
        migrate_data(source, target)
        os.replace(migrating_path, sqlite_path)
    except Exception:
        _remove_sqlite_files(migrating_path)
        raise
    return SqliteDataStore(sqlite_path)


def _remove_sqlite_files(database_path: Path) -> None:
    for candidate in (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ):
        if candidate.exists():
            candidate.unlink()
