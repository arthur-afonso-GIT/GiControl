import sqlite3
import json
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

from backend.infrastructure.default_data import default_data


def _to_cents(value) -> int:
    return int(
        (Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    )


def _from_cents(value: int) -> float:
    return float(Decimal(value) / 100)


class SqliteDataStore:
    """Persistência SQLite normalizada compatível com a porta transitória DataStore."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path).resolve()

    def load(self) -> dict:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            self._ensure_schema(connection)
            data = self._read(connection)
        if not any(data.values()):
            data = default_data()
            self.save(data)
        return data

    def save(self, data: dict) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            self._ensure_schema(connection)
            with connection:
                connection.execute("DELETE FROM transactions")
                connection.execute("DELETE FROM scheduled_expenses")
                connection.execute("DELETE FROM card_invoices")
                connection.execute("DELETE FROM card_installments")
                connection.execute("DELETE FROM card_purchases")
                connection.execute("DELETE FROM credit_cards")
                connection.execute("DELETE FROM accounts")
                connection.execute("DELETE FROM categories")
                connection.executemany(
                    """INSERT INTO accounts
                       (id, name, type, balance_cents, monthly_income_cents,
                        income_day, income_category_id, income_start_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            account["id"],
                            account["name"],
                            account["type"],
                            _to_cents(account.get("balance", 0)),
                            _to_cents(account.get("monthly_income", 0)),
                            account.get("income_day"),
                            account.get("income_category_id"),
                            account.get("income_start_date"),
                        )
                        for account in data["accounts"]
                    ],
                )
                connection.executemany(
                    """INSERT INTO scheduled_expenses
                       (id, name, amount_cents, account_id, category_id, due_day, start_date, end_date, active, exceptions_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [(item["id"], item["name"], _to_cents(item["amount"]), item["account_id"], item["category_id"],
                      item["due_day"], item["start_date"], item.get("end_date"), int(item.get("active", True)), json.dumps(item.get("exceptions", [])))
                     for item in data.get("scheduled_expenses", [])],
                )
                connection.executemany(
                    """INSERT INTO categories
                       (id, name, type, monthly_limit_cents)
                       VALUES (?, ?, ?, ?)""",
                    [
                        (
                            category["id"],
                            category["name"],
                            category["type"],
                            _to_cents(category.get("monthly_limit", 0)),
                        )
                        for category in data["categories"]
                    ],
                )
                connection.executemany(
                    """INSERT INTO transactions
                       (id, amount_cents, date, category_id, account_id,
                        description, type, is_fixed, installment_group_id,
                        installment_number, installment_total)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            transaction["id"],
                            _to_cents(transaction["amount"]),
                            transaction["date"],
                            transaction["category_id"],
                            transaction["account_id"],
                            transaction["description"],
                            transaction["type"],
                            int(transaction.get("is_fixed", False)),
                            transaction.get("installment_group_id"),
                            transaction.get("installment_number", 1),
                            transaction.get("installment_total", 1),
                        )
                        for transaction in data["transactions"]
                    ],
                )
                connection.executemany("""INSERT INTO credit_cards
                    (id,name,credit_limit_cents,closing_day,due_day,payment_account_id,active) VALUES (?,?,?,?,?,?,?)""",
                    [(x["id"],x["name"],_to_cents(x["credit_limit"]),x["closing_day"],x["due_day"],x["payment_account_id"],int(x.get("active",True))) for x in data.get("credit_cards",[])])
                connection.executemany("""INSERT INTO card_purchases
                    (id,card_id,category_id,description,purchase_date,total_amount_cents,installments) VALUES (?,?,?,?,?,?,?)""",
                    [(x["id"],x["card_id"],x["category_id"],x["description"],x["purchase_date"],_to_cents(x["total_amount"]),x["installments"]) for x in data.get("card_purchases",[])])
                connection.executemany("""INSERT INTO card_installments
                    (id,purchase_id,card_id,category_id,description,amount_cents,number,total,invoice_month) VALUES (?,?,?,?,?,?,?,?,?)""",
                    [(x["id"],x["purchase_id"],x["card_id"],x["category_id"],x["description"],_to_cents(x["amount"]),x["number"],x["total"],x["invoice_month"]) for x in data.get("card_installments",[])])
                connection.executemany("""INSERT INTO card_invoices
                    (id,card_id,reference_month,closing_date,due_date,total_cents,status,paid_at,payment_transaction_id) VALUES (?,?,?,?,?,?,?,?,?)""",
                    [(x["id"],x["card_id"],x["reference_month"],x["closing_date"],x["due_date"],_to_cents(x["total"]),x["status"],x.get("paid_at"),x.get("payment_transaction_id")) for x in data.get("card_invoices",[])])

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.file_path)
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _ensure_schema(connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                balance_cents INTEGER NOT NULL,
                monthly_income_cents INTEGER NOT NULL,
                income_day INTEGER,
                income_category_id TEXT,
                income_start_date TEXT
            );
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                monthly_limit_cents INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                amount_cents INTEGER NOT NULL,
                date TEXT NOT NULL,
                category_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                description TEXT NOT NULL,
                type TEXT NOT NULL,
                is_fixed INTEGER NOT NULL DEFAULT 0
                ,installment_group_id TEXT
                ,installment_number INTEGER NOT NULL DEFAULT 1
                ,installment_total INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS scheduled_expenses (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, amount_cents INTEGER NOT NULL,
                account_id TEXT NOT NULL, category_id TEXT NOT NULL, due_day INTEGER NOT NULL,
                start_date TEXT NOT NULL, end_date TEXT, active INTEGER NOT NULL DEFAULT 1,
                exceptions_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS credit_cards (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, credit_limit_cents INTEGER NOT NULL,
                closing_day INTEGER NOT NULL, due_day INTEGER NOT NULL, payment_account_id TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS card_purchases (
                id TEXT PRIMARY KEY, card_id TEXT NOT NULL, category_id TEXT NOT NULL,
                description TEXT NOT NULL, purchase_date TEXT NOT NULL,
                total_amount_cents INTEGER NOT NULL, installments INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS card_installments (
                id TEXT PRIMARY KEY, purchase_id TEXT NOT NULL, card_id TEXT NOT NULL, category_id TEXT NOT NULL,
                description TEXT NOT NULL, amount_cents INTEGER NOT NULL, number INTEGER NOT NULL,
                total INTEGER NOT NULL, invoice_month TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS card_invoices (
                id TEXT PRIMARY KEY, card_id TEXT NOT NULL, reference_month TEXT NOT NULL,
                closing_date TEXT NOT NULL, due_date TEXT NOT NULL, total_cents INTEGER NOT NULL,
                status TEXT NOT NULL, paid_at TEXT, payment_transaction_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_transactions_account
                ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_date
                ON transactions(date);
            """
        )
        account_columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
        account_migrations = {
            "income_day": "ALTER TABLE accounts ADD COLUMN income_day INTEGER",
            "income_category_id": "ALTER TABLE accounts ADD COLUMN income_category_id TEXT",
            "income_start_date": "ALTER TABLE accounts ADD COLUMN income_start_date TEXT",
        }
        for column, statement in account_migrations.items():
            if column not in account_columns:
                connection.execute(statement)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(transactions)")}
        migrations = {
            "installment_group_id": "ALTER TABLE transactions ADD COLUMN installment_group_id TEXT",
            "installment_number": "ALTER TABLE transactions ADD COLUMN installment_number INTEGER NOT NULL DEFAULT 1",
            "installment_total": "ALTER TABLE transactions ADD COLUMN installment_total INTEGER NOT NULL DEFAULT 1",
        }
        for column, statement in migrations.items():
            if column not in columns:
                connection.execute(statement)
        scheduled_columns = {row[1] for row in connection.execute("PRAGMA table_info(scheduled_expenses)")}
        if "exceptions_json" not in scheduled_columns:
            connection.execute("ALTER TABLE scheduled_expenses ADD COLUMN exceptions_json TEXT NOT NULL DEFAULT '[]'")

    @staticmethod
    def _read(connection) -> dict:
        accounts = [
            {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "balance": _from_cents(row[3]),
                "monthly_income": _from_cents(row[4]),
                **({"income_day": row[5], "income_category_id": row[6], "income_start_date": row[7]} if row[5] is not None else {}),
            }
            for row in connection.execute(
                """SELECT id, name, type, balance_cents, monthly_income_cents,
                          income_day, income_category_id, income_start_date
                   FROM accounts ORDER BY rowid"""
            )
        ]
        categories = [
            {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "monthly_limit": _from_cents(row[3]),
            }
            for row in connection.execute(
                "SELECT id, name, type, monthly_limit_cents FROM categories ORDER BY rowid"
            )
        ]
        transactions = []
        for row in connection.execute(
                """SELECT id, amount_cents, date, category_id, account_id,
                          description, type, is_fixed, installment_group_id,
                          installment_number, installment_total
                   FROM transactions ORDER BY rowid"""):
            record = {
                "id": row[0],
                "amount": _from_cents(row[1]),
                "date": row[2],
                "category_id": row[3],
                "account_id": row[4],
                "description": row[5],
                "type": row[6],
                "is_fixed": bool(row[7]),
            }
            if row[8]:
                record.update({"installment_group_id": row[8], "installment_number": row[9], "installment_total": row[10]})
            transactions.append(record)
        result = {
            "accounts": accounts,
            "categories": categories,
            "transactions": transactions,
        }
        scheduled = [{"id": row[0], "name": row[1], "amount": _from_cents(row[2]), "account_id": row[3],
                      "category_id": row[4], "due_day": row[5], "start_date": row[6], "end_date": row[7], "active": bool(row[8]),
                      "exceptions": json.loads(row[9] or "[]")}
                     for row in connection.execute("""SELECT id, name, amount_cents, account_id, category_id,
                        due_day, start_date, end_date, active, exceptions_json FROM scheduled_expenses ORDER BY rowid""")]
        if scheduled: result["scheduled_expenses"] = scheduled
        cards = [{"id":r[0],"name":r[1],"credit_limit":_from_cents(r[2]),"closing_day":r[3],"due_day":r[4],"payment_account_id":r[5],"active":bool(r[6])} for r in connection.execute("SELECT id,name,credit_limit_cents,closing_day,due_day,payment_account_id,active FROM credit_cards ORDER BY rowid")]
        purchases = [{"id":r[0],"card_id":r[1],"category_id":r[2],"description":r[3],"purchase_date":r[4],"total_amount":_from_cents(r[5]),"installments":r[6]} for r in connection.execute("SELECT id,card_id,category_id,description,purchase_date,total_amount_cents,installments FROM card_purchases ORDER BY rowid")]
        installments = [{"id":r[0],"purchase_id":r[1],"card_id":r[2],"category_id":r[3],"description":r[4],"amount":_from_cents(r[5]),"number":r[6],"total":r[7],"invoice_month":r[8]} for r in connection.execute("SELECT id,purchase_id,card_id,category_id,description,amount_cents,number,total,invoice_month FROM card_installments ORDER BY rowid")]
        invoices = [{"id":r[0],"card_id":r[1],"reference_month":r[2],"closing_date":r[3],"due_date":r[4],"total":_from_cents(r[5]),"status":r[6],"paid_at":r[7],"payment_transaction_id":r[8]} for r in connection.execute("SELECT id,card_id,reference_month,closing_date,due_date,total_cents,status,paid_at,payment_transaction_id FROM card_invoices ORDER BY rowid")]
        for key, values in (("credit_cards",cards),("card_purchases",purchases),("card_installments",installments),("card_invoices",invoices)):
            if values: result[key]=values
        return result
