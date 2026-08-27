"""Adaptadores de infraestrutura da GiControl."""

from backend.infrastructure.data_migration import MigrationResult, migrate_data
from backend.infrastructure.json_file_data_store import JsonFileDataStore
from backend.infrastructure.persistence_bootstrap import create_default_data_store
from backend.infrastructure.service_container import (
    ServiceContainer,
    create_default_service_container,
)
from backend.infrastructure.sqlite_data_store import SqliteDataStore
from backend.infrastructure.unit_of_work import JsonUnitOfWork

__all__ = [
    "JsonFileDataStore",
    "JsonUnitOfWork",
    "MigrationResult",
    "ServiceContainer",
    "SqliteDataStore",
    "create_default_data_store",
    "create_default_service_container",
    "migrate_data",
]
