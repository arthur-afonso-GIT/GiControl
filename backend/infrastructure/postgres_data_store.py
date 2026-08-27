import json
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_EVEN

from backend.infrastructure.default_data import default_data


def _to_cents(value) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _from_cents(value: int) -> float:
    return float(Decimal(value) / 100)


class PostgresDataStore:
    """Adaptador PostgreSQL transitório para Supabase e outros provedores compatíveis."""

    def __init__(self, database_url: str):
        if (not database_url or not database_url.startswith(("postgres://", "postgresql://"))
                or "[" in database_url or "]" in database_url):
            raise ValueError(
                "DATABASE_URL deve ser a connection string PostgreSQL do Session pooler "
                "(começando com postgresql://) e não pode conter campos [PENDENTES]"
            )
        self.database_url = database_url

    def load(self) -> dict:
        with self._connection() as connection:
            self._ensure_schema(connection)
            data = self._read(connection)
        if not any(data.values()):
            data = default_data()
            self.save(data)
        return data

    def save(self, data: dict) -> None:
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM card_invoices")
                    cursor.execute("DELETE FROM card_installments")
                    cursor.execute("DELETE FROM card_purchases")
                    cursor.execute("DELETE FROM credit_cards")
                    cursor.execute("DELETE FROM transactions")
                    cursor.execute("DELETE FROM scheduled_expenses")
                    cursor.execute("DELETE FROM accounts")
                    cursor.execute("DELETE FROM categories")
                    cursor.executemany(
                        """INSERT INTO accounts
                           (id, name, type, balance_cents, monthly_income_cents,
                            income_day, income_category_id, income_start_date)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(item["id"], item["name"], item["type"], _to_cents(item.get("balance", 0)),
                          _to_cents(item.get("monthly_income", 0)), item.get("income_day"),
                          item.get("income_category_id"), item.get("income_start_date"))
                         for item in data["accounts"]],
                    )
                    cursor.executemany(
                        """INSERT INTO categories (id, name, type, monthly_limit_cents)
                           VALUES (%s, %s, %s, %s)""",
                        [(item["id"], item["name"], item["type"], _to_cents(item.get("monthly_limit", 0)))
                         for item in data["categories"]],
                    )
                    cursor.executemany(
                        """INSERT INTO scheduled_expenses
                           (id, name, amount_cents, account_id, category_id, due_day,
                            start_date, end_date, active, exceptions_json)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)""",
                        [(item["id"], item["name"], _to_cents(item["amount"]), item["account_id"],
                          item["category_id"], item["due_day"], item["start_date"], item.get("end_date"),
                          item.get("active", True), json.dumps(item.get("exceptions", [])))
                         for item in data.get("scheduled_expenses", [])],
                    )
                    cursor.executemany(
                        """INSERT INTO transactions
                           (id, amount_cents, date, category_id, account_id, description, type,
                            is_fixed, installment_group_id, installment_number, installment_total)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(item["id"], _to_cents(item["amount"]), item["date"], item["category_id"],
                          item["account_id"], item["description"], item["type"], item.get("is_fixed", False),
                          item.get("installment_group_id"), item.get("installment_number", 1),
                          item.get("installment_total", 1)) for item in data["transactions"]],
                    )
                    cursor.executemany(
                        """INSERT INTO credit_cards VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        [(item["id"], item["name"], _to_cents(item["credit_limit"]), item["closing_day"],
                          item["due_day"], item["payment_account_id"], item.get("active", True))
                         for item in data.get("credit_cards", [])],
                    )
                    cursor.executemany(
                        """INSERT INTO card_purchases VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        [(item["id"], item["card_id"], item["category_id"], item["description"],
                          item["purchase_date"], _to_cents(item["total_amount"]), item["installments"])
                         for item in data.get("card_purchases", [])],
                    )
                    cursor.executemany(
                        """INSERT INTO card_installments VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(item["id"], item["purchase_id"], item["card_id"], item["category_id"],
                          item["description"], _to_cents(item["amount"]), item["number"], item["total"],
                          item["invoice_month"]) for item in data.get("card_installments", [])],
                    )
                    cursor.executemany(
                        """INSERT INTO card_invoices VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(item["id"], item["card_id"], item["reference_month"], item["closing_date"],
                          item["due_date"], _to_cents(item["total"]), item["status"], item.get("paid_at"),
                          item.get("payment_transaction_id")) for item in data.get("card_invoices", [])],
                    )

    @contextmanager
    def _connection(self):
        try:
            import psycopg
        except ImportError as error:
            raise RuntimeError("Instale as dependências com 'pip install -r requirements.txt'") from error
        with psycopg.connect(self.database_url, connect_timeout=10) as connection:
            yield connection

    @staticmethod
    def _ensure_schema(connection) -> None:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
                    balance_cents BIGINT NOT NULL, monthly_income_cents BIGINT NOT NULL,
                    income_day INTEGER, income_category_id TEXT, income_start_date DATE
                );
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
                    monthly_limit_cents BIGINT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY, amount_cents BIGINT NOT NULL, date DATE NOT NULL,
                    category_id TEXT NOT NULL, account_id TEXT NOT NULL, description TEXT NOT NULL,
                    type TEXT NOT NULL, is_fixed BOOLEAN NOT NULL DEFAULT FALSE,
                    installment_group_id TEXT, installment_number INTEGER NOT NULL DEFAULT 1,
                    installment_total INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS scheduled_expenses (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, amount_cents BIGINT NOT NULL,
                    account_id TEXT NOT NULL, category_id TEXT NOT NULL, due_day INTEGER NOT NULL,
                    start_date DATE NOT NULL, end_date DATE, active BOOLEAN NOT NULL DEFAULT TRUE,
                    exceptions_json JSONB NOT NULL DEFAULT '[]'::jsonb
                );
                CREATE TABLE IF NOT EXISTS credit_cards (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, credit_limit_cents BIGINT NOT NULL,
                    closing_day INTEGER NOT NULL, due_day INTEGER NOT NULL,
                    payment_account_id TEXT NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE
                );
                CREATE TABLE IF NOT EXISTS card_purchases (
                    id TEXT PRIMARY KEY, card_id TEXT NOT NULL, category_id TEXT NOT NULL,
                    description TEXT NOT NULL, purchase_date DATE NOT NULL,
                    total_amount_cents BIGINT NOT NULL, installments INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS card_installments (
                    id TEXT PRIMARY KEY, purchase_id TEXT NOT NULL, card_id TEXT NOT NULL,
                    category_id TEXT NOT NULL, description TEXT NOT NULL, amount_cents BIGINT NOT NULL,
                    number INTEGER NOT NULL, total INTEGER NOT NULL, invoice_month DATE NOT NULL
                );
                CREATE TABLE IF NOT EXISTS card_invoices (
                    id TEXT PRIMARY KEY, card_id TEXT NOT NULL, reference_month DATE NOT NULL,
                    closing_date DATE NOT NULL, due_date DATE NOT NULL, total_cents BIGINT NOT NULL,
                    status TEXT NOT NULL, paid_at DATE, payment_transaction_id TEXT,
                    UNIQUE(card_id, reference_month)
                );
                CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
                CREATE INDEX IF NOT EXISTS idx_card_installments_invoice ON card_installments(card_id, invoice_month);
                ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
                ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
                ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
                ALTER TABLE scheduled_expenses ENABLE ROW LEVEL SECURITY;
                ALTER TABLE credit_cards ENABLE ROW LEVEL SECURITY;
                ALTER TABLE card_purchases ENABLE ROW LEVEL SECURITY;
                ALTER TABLE card_installments ENABLE ROW LEVEL SECURITY;
                ALTER TABLE card_invoices ENABLE ROW LEVEL SECURITY;
            """)
        connection.commit()

    @staticmethod
    def _read(connection) -> dict:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT id, name, type, balance_cents, monthly_income_cents,
                                      income_day, income_category_id, income_start_date
                               FROM accounts ORDER BY id""")
            accounts = [{"id": row[0], "name": row[1], "type": row[2], "balance": _from_cents(row[3]),
                         "monthly_income": _from_cents(row[4]),
                         **({"income_day": row[5], "income_category_id": row[6],
                            "income_start_date": row[7].isoformat()} if row[5] is not None else {})}
                        for row in cursor.fetchall()]
            cursor.execute("SELECT id, name, type, monthly_limit_cents FROM categories ORDER BY id")
            categories = [{"id": row[0], "name": row[1], "type": row[2],
                           "monthly_limit": _from_cents(row[3])} for row in cursor.fetchall()]
            cursor.execute("""SELECT id, amount_cents, date, category_id, account_id, description,
                                      type, is_fixed, installment_group_id, installment_number, installment_total
                               FROM transactions ORDER BY date, id""")
            transactions = []
            for row in cursor.fetchall():
                item = {"id": row[0], "amount": _from_cents(row[1]), "date": row[2].isoformat(),
                        "category_id": row[3], "account_id": row[4], "description": row[5],
                        "type": row[6], "is_fixed": row[7]}
                if row[8]:
                    item.update({"installment_group_id": row[8], "installment_number": row[9],
                                 "installment_total": row[10]})
                transactions.append(item)
            cursor.execute("""SELECT id, name, amount_cents, account_id, category_id, due_day,
                                      start_date, end_date, active, exceptions_json
                               FROM scheduled_expenses ORDER BY id""")
            scheduled = [{"id": row[0], "name": row[1], "amount": _from_cents(row[2]),
                          "account_id": row[3], "category_id": row[4], "due_day": row[5],
                          "start_date": row[6].isoformat(), "end_date": row[7].isoformat() if row[7] else None,
                          "active": row[8], "exceptions": row[9] if isinstance(row[9], list) else json.loads(row[9])}
                         for row in cursor.fetchall()]
            cursor.execute("SELECT id,name,credit_limit_cents,closing_day,due_day,payment_account_id,active FROM credit_cards ORDER BY id")
            cards = [{"id":r[0],"name":r[1],"credit_limit":_from_cents(r[2]),"closing_day":r[3],"due_day":r[4],"payment_account_id":r[5],"active":r[6]} for r in cursor.fetchall()]
            cursor.execute("SELECT id,card_id,category_id,description,purchase_date,total_amount_cents,installments FROM card_purchases ORDER BY purchase_date,id")
            purchases = [{"id":r[0],"card_id":r[1],"category_id":r[2],"description":r[3],"purchase_date":r[4].isoformat(),"total_amount":_from_cents(r[5]),"installments":r[6]} for r in cursor.fetchall()]
            cursor.execute("SELECT id,purchase_id,card_id,category_id,description,amount_cents,number,total,invoice_month FROM card_installments ORDER BY invoice_month,id")
            installments = [{"id":r[0],"purchase_id":r[1],"card_id":r[2],"category_id":r[3],"description":r[4],"amount":_from_cents(r[5]),"number":r[6],"total":r[7],"invoice_month":r[8].isoformat()} for r in cursor.fetchall()]
            cursor.execute("SELECT id,card_id,reference_month,closing_date,due_date,total_cents,status,paid_at,payment_transaction_id FROM card_invoices ORDER BY reference_month,id")
            invoices = [{"id":r[0],"card_id":r[1],"reference_month":r[2].isoformat(),"closing_date":r[3].isoformat(),"due_date":r[4].isoformat(),"total":_from_cents(r[5]),"status":r[6],"paid_at":r[7].isoformat() if r[7] else None,"payment_transaction_id":r[8]} for r in cursor.fetchall()]
        result = {"accounts": accounts, "categories": categories, "transactions": transactions,
                  "credit_cards": cards, "card_purchases": purchases,
                  "card_installments": installments, "card_invoices": invoices}
        if scheduled:
            result["scheduled_expenses"] = scheduled
        return result
