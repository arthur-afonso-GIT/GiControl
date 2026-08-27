from dataclasses import dataclass

from backend.application.ports import DataStore
from backend.infrastructure.default_data import default_data


@dataclass(frozen=True, slots=True)
class MigrationResult:
    accounts: int
    categories: int
    transactions: int


def migrate_data(source: DataStore, target: DataStore, overwrite: bool = False) -> MigrationResult:
    """Copia e verifica dados entre stores, protegendo destinos já utilizados."""
    source_data = source.load()
    target_data = target.load()
    if not overwrite and target_data != default_data():
        raise ValueError("O destino já contém dados; migração cancelada")

    target.save(source_data)
    migrated = target.load()
    if _canonical(migrated) != _canonical(source_data):
        raise RuntimeError("A verificação pós-migração encontrou divergências")
    return MigrationResult(
        accounts=len(migrated["accounts"]),
        categories=len(migrated["categories"]),
        transactions=len(migrated["transactions"]),
    )


def _canonical(data: dict) -> dict:
    """Compara conteúdo sem depender da ordem física escolhida pelo banco."""
    return {
        key: sorted(value, key=lambda item: item.get("id", "")) if isinstance(value, list) else value
        for key, value in data.items()
    }
