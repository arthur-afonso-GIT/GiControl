import argparse
from pathlib import Path

from backend.infrastructure.data_migration import migrate_data
from backend.infrastructure.json_file_data_store import JsonFileDataStore
from backend.infrastructure.postgres_data_store import PostgresDataStore
from backend.infrastructure.sqlite_data_store import SqliteDataStore
from backend.infrastructure.environment import database_url, load_project_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra dados locais da GiControl para PostgreSQL/Supabase")
    parser.add_argument("--source", choices=("sqlite", "json"), default="sqlite")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--execute", action="store_true", help="Confirma a gravação no banco remoto")
    parser.add_argument("--overwrite", action="store_true", help="Substitui um destino que já contém dados")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    load_project_environment(project_dir)
    source = (SqliteDataStore(project_dir / "data" / "fincontrol.db") if args.source == "sqlite"
              else JsonFileDataStore(project_dir / "data" / "data.json"))
    local = source.load()
    counts = {key: len(local.get(key, [])) for key in
              ("accounts", "categories", "transactions", "scheduled_expenses")}
    print("Origem validada:", ", ".join(f"{value} {key}" for key, value in counts.items()))
    if not args.execute:
        print("Simulação concluída. Use --execute para iniciar a migração.")
        return

    url = database_url()
    if not url:
        raise SystemExit("Defina DATABASE_URL no arquivo .env antes de executar a migração")
    if not url.startswith(("postgres://", "postgresql://")) or "[" in url or "]" in url:
        raise SystemExit("DATABASE_URL incompleta: substitua todos os campos entre colchetes pela Session pooler connection string")
    result = migrate_data(source, PostgresDataStore(url), overwrite=args.overwrite)
    print(f"Migração verificada: {result.accounts} contas, {result.categories} categorias, "
          f"{result.transactions} transações.")


if __name__ == "__main__":
    main()
