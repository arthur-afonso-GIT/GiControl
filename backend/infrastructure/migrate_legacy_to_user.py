import argparse
import os
import re
from pathlib import Path

import httpx

from backend.infrastructure.environment import load_project_environment
from backend.infrastructure.auth_context import current_user_id
from backend.infrastructure.postgres_unit_of_work import PostgresUnitOfWork

TABLES = ("accounts","categories","transactions","scheduled_expenses","credit_cards",
          "card_purchases","card_installments","card_invoices")
FINANCIAL_TABLES = tuple(item for item in TABLES if item != "categories")


def schema_for(user_id: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", user_id):
        raise ValueError("ID de usuário inválido")
    return "user_" + user_id.replace("-", "_")


def resolve_user_id(email: str) -> str:
    url=os.environ["SUPABASE_URL"].rstrip("/");key=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    response=httpx.get(f"{url}/auth/v1/admin/users?page=1&per_page=1000",
        headers={"apikey":key,"Authorization":f"Bearer {key}"},timeout=15)
    response.raise_for_status()
    matches=[item["id"] for item in response.json().get("users",[]) if item.get("email","").casefold()==email.casefold()]
    if len(matches)!=1:raise ValueError("E-mail não identifica exatamente um usuário")
    return matches[0]


def migrate(database_url: str, user_id: str, overwrite: bool = False) -> dict[str,int]:
    import psycopg
    from psycopg import sql
    schema=schema_for(user_id)
    token=current_user_id.set(user_id)
    try:
        connection=PostgresUnitOfWork(database_url)._connect()
        connection.close()
    finally:current_user_id.reset(token)
    with psycopg.connect(database_url,connect_timeout=10) as connection:
        with connection.transaction(),connection.cursor() as cursor:
            target=sql.Identifier(schema)
            counts={}
            for table in FINANCIAL_TABLES:
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(target,sql.Identifier(table)))
                counts[table]=cursor.fetchone()[0]
            if any(counts.values()) and not overwrite:
                raise ValueError("O usuário já possui dados; use --overwrite somente após conferir o destino")
            for table in reversed(TABLES):
                cursor.execute(sql.SQL("DELETE FROM {}.{}").format(target,sql.Identifier(table)))
            for table in TABLES:
                name=sql.Identifier(table)
                cursor.execute(sql.SQL("INSERT INTO {}.{} SELECT * FROM public.{}").format(target,name,name))
            verified={}
            for table in TABLES:
                name=sql.Identifier(table)
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM public.{}").format(name));source=cursor.fetchone()[0]
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(target,name));destination=cursor.fetchone()[0]
                if source!=destination:raise RuntimeError(f"Falha de verificação em {table}: {source} != {destination}")
                verified[table]=destination
            return verified


def main():
    parser=argparse.ArgumentParser(description="Copia dados legados públicos para um usuário autenticado")
    identity=parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--user-id");identity.add_argument("--email")
    parser.add_argument("--overwrite",action="store_true")
    args=parser.parse_args();load_project_environment(Path.cwd())
    user=args.user_id or resolve_user_id(args.email)
    result=migrate(os.environ["DATABASE_URL"],user,args.overwrite)
    print("Migração verificada:",", ".join(f"{key}={value}" for key,value in result.items()))


if __name__=="__main__":main()
