import json
import re
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from types import TracebackType
from typing import Self
from threading import Lock

from backend.domain import Account, AccountType, CardInstallment, CardInvoice, CardPurchase, Category, CreditCard, InvoiceStatus, Money, OccurrenceException, RecurringExpense, Transaction, TransactionType
from backend.infrastructure.auth_context import user_id
from backend.infrastructure.default_data import default_data

_initialized_user_schemas: set[str] = set()
_schema_lock = Lock()


def _cents(value) -> int:
    amount = value.amount if isinstance(value, Money) else value
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


class PostgresUnitOfWork:
    """Unit of Work SQL: commits isolados e rollback atômico em casos de uso compostos."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._active_connection = None
        self.accounts = PostgresAccountRepository(self)
        self.categories = PostgresCategoryRepository(self)
        self.transactions = PostgresTransactionRepository(self)
        self.recurring_expenses = PostgresRecurringExpenseRepository(self)
        self.credit_cards = PostgresCreditCardRepository(self)
        self.card_purchases = PostgresCardPurchaseRepository(self)
        self.card_installments = PostgresCardInstallmentRepository(self)
        self.card_invoices = PostgresCardInvoiceRepository(self)

    def __enter__(self) -> Self:
        if self._active_connection is not None:
            raise RuntimeError("Unidades de trabalho aninhadas não são suportadas")
        self._active_connection = self._connect()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None,
                 traceback: TracebackType | None) -> bool:
        connection = self._active_connection
        try:
            if exc_type is None: connection.commit()
            else: connection.rollback()
        finally:
            connection.close()
            self._active_connection = None
        return False

    def _connect(self):
        try: import psycopg
        except ImportError as error: raise RuntimeError("Instale as dependências com 'pip install -r requirements.txt'") from error
        connection = psycopg.connect(self.database_url, connect_timeout=10)
        owner = user_id()
        if owner:
            schema = "user_" + re.sub(r"[^a-zA-Z0-9_]", "_", owner)
            with connection.cursor() as cursor:
                cursor.execute(psycopg.sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(psycopg.sql.Identifier(schema)))
                cursor.execute(psycopg.sql.SQL("SET search_path TO {}").format(psycopg.sql.Identifier(schema)))
            with _schema_lock:
                if schema not in _initialized_user_schemas:
                    from backend.infrastructure.postgres_data_store import PostgresDataStore
                    PostgresDataStore._ensure_schema(connection)
                    self._seed_categories(connection, owner)
                    _initialized_user_schemas.add(schema)
            connection.commit()
        return connection

    @staticmethod
    def _seed_categories(connection, owner: str) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM categories")
            if cursor.fetchone()[0]: return
            values=[(f"{owner}:{item['id']}",item["name"],item["type"],_cents(item.get("monthly_limit",0)))
                for item in default_data()["categories"]]
            cursor.executemany("INSERT INTO categories (id,name,type,monthly_limit_cents) VALUES (%s,%s,%s,%s)",values)

    @contextmanager
    def cursor(self):
        owned = self._active_connection is None
        connection = self._connect() if owned else self._active_connection
        try:
            with connection.cursor() as cursor: yield cursor
            if owned: connection.commit()
        except Exception:
            if owned: connection.rollback()
            raise
        finally:
            if owned: connection.close()


class PostgresAccountRepository:
    def __init__(self, uow): self.uow = uow
    def list_all(self):
        with self.uow.cursor() as c:
            c.execute("SELECT id,name,type,balance_cents,monthly_income_cents,income_day,income_category_id,income_start_date FROM accounts ORDER BY id")
            return [self._domain(row) for row in c.fetchall()]
    def get(self, account_id):
        with self.uow.cursor() as c:
            c.execute("SELECT id,name,type,balance_cents,monthly_income_cents,income_day,income_category_id,income_start_date FROM accounts WHERE id=%s", (account_id,))
            row = c.fetchone(); return self._domain(row) if row else None
    def save(self, item):
        with self.uow.cursor() as c: c.execute("""INSERT INTO accounts VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,type=EXCLUDED.type,balance_cents=EXCLUDED.balance_cents,
            monthly_income_cents=EXCLUDED.monthly_income_cents,income_day=EXCLUDED.income_day,
            income_category_id=EXCLUDED.income_category_id,income_start_date=EXCLUDED.income_start_date""",
            (item.id,item.name,item.account_type.value,_cents(item.balance),_cents(item.monthly_income),item.income_day,item.income_category_id,item.income_start_date))
        return item
    def delete(self, item_id):
        with self.uow.cursor() as c: c.execute("DELETE FROM accounts WHERE id=%s", (item_id,)); return c.rowcount > 0
    @staticmethod
    def _domain(row): return Account(row[0],row[1],AccountType(row[2]),Money.from_value(Decimal(row[3])/100),Money.from_value(Decimal(row[4])/100),row[5],row[6],row[7])


class PostgresCategoryRepository:
    def __init__(self, uow): self.uow = uow
    def list_all(self):
        with self.uow.cursor() as c: c.execute("SELECT id,name,type,monthly_limit_cents FROM categories ORDER BY id"); return [self._domain(r) for r in c.fetchall()]
    def get(self, item_id):
        with self.uow.cursor() as c: c.execute("SELECT id,name,type,monthly_limit_cents FROM categories WHERE id=%s",(item_id,)); r=c.fetchone(); return self._domain(r) if r else None
    def save(self, item):
        with self.uow.cursor() as c: c.execute("""INSERT INTO categories VALUES (%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET
            name=EXCLUDED.name,type=EXCLUDED.type,monthly_limit_cents=EXCLUDED.monthly_limit_cents""",(item.id,item.name,item.category_type.value,_cents(item.monthly_limit)))
        return item
    def delete(self, item_id):
        with self.uow.cursor() as c: c.execute("DELETE FROM categories WHERE id=%s",(item_id,)); return c.rowcount > 0
    @staticmethod
    def _domain(r): return Category(r[0],r[1],TransactionType(r[2]),Money.from_value(Decimal(r[3])/100))


class PostgresTransactionRepository:
    FIELDS="id,amount_cents,date,category_id,account_id,description,type,is_fixed,installment_group_id,installment_number,installment_total"
    def __init__(self, uow): self.uow=uow
    def list_all(self):
        with self.uow.cursor() as c: c.execute(f"SELECT {self.FIELDS} FROM transactions ORDER BY date,id"); return [self._domain(r) for r in c.fetchall()]
    def get(self,item_id):
        with self.uow.cursor() as c: c.execute(f"SELECT {self.FIELDS} FROM transactions WHERE id=%s",(item_id,)); r=c.fetchone(); return self._domain(r) if r else None
    def save(self,item): self.save_all([item]); return item
    def save_all(self,items):
        if not items: return []
        with self.uow.cursor() as c: c.executemany("""INSERT INTO transactions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(id) DO UPDATE SET amount_cents=EXCLUDED.amount_cents,date=EXCLUDED.date,category_id=EXCLUDED.category_id,
            account_id=EXCLUDED.account_id,description=EXCLUDED.description,type=EXCLUDED.type,is_fixed=EXCLUDED.is_fixed,
            installment_group_id=EXCLUDED.installment_group_id,installment_number=EXCLUDED.installment_number,installment_total=EXCLUDED.installment_total""",
            [(i.id,_cents(i.amount),i.date,i.category_id,i.account_id,i.description,i.transaction_type.value,i.is_fixed,i.installment_group_id,i.installment_number,i.installment_total) for i in items])
        return items
    def delete(self,item_id): return self._delete("id",item_id)>0
    def delete_by_account(self,item_id): return self._delete("account_id",item_id)
    def delete_by_installment_group(self,item_id): return self._delete("installment_group_id",item_id)
    def _delete(self,column,value):
        with self.uow.cursor() as c: c.execute(f"DELETE FROM transactions WHERE {column}=%s",(value,)); return c.rowcount
    @staticmethod
    def _domain(r): return Transaction(r[0],Money.from_value(Decimal(r[1])/100),r[2],r[3],r[4],r[5],TransactionType(r[6]),r[7],r[8],r[9],r[10])


class PostgresRecurringExpenseRepository:
    FIELDS="id,name,amount_cents,account_id,category_id,due_day,start_date,end_date,active,exceptions_json"
    def __init__(self,uow): self.uow=uow
    def list_all(self):
        with self.uow.cursor() as c: c.execute(f"SELECT {self.FIELDS} FROM scheduled_expenses ORDER BY id"); return [self._domain(r) for r in c.fetchall()]
    def get(self,item_id):
        with self.uow.cursor() as c: c.execute(f"SELECT {self.FIELDS} FROM scheduled_expenses WHERE id=%s",(item_id,)); r=c.fetchone(); return self._domain(r) if r else None
    def save(self,i):
        exceptions=[{"month":e.month,"due_date":e.due_date.isoformat() if e.due_date else None,"skipped":e.skipped} for e in i.exceptions]
        with self.uow.cursor() as c: c.execute("""INSERT INTO scheduled_expenses VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,amount_cents=EXCLUDED.amount_cents,account_id=EXCLUDED.account_id,
            category_id=EXCLUDED.category_id,due_day=EXCLUDED.due_day,start_date=EXCLUDED.start_date,end_date=EXCLUDED.end_date,
            active=EXCLUDED.active,exceptions_json=EXCLUDED.exceptions_json""",(i.id,i.name,_cents(i.amount),i.account_id,i.category_id,i.due_day,i.start_date,i.end_date,i.active,json.dumps(exceptions)))
        return i
    def delete(self,item_id):
        with self.uow.cursor() as c: c.execute("DELETE FROM scheduled_expenses WHERE id=%s",(item_id,)); return c.rowcount>0
    @staticmethod
    def _domain(r):
        values=r[9] if isinstance(r[9],list) else json.loads(r[9] or "[]")
        return RecurringExpense(r[0],r[1],Money.from_value(Decimal(r[2])/100),r[3],r[4],r[5],r[6],r[7],r[8],tuple(OccurrenceException(v["month"],date.fromisoformat(v["due_date"]) if v.get("due_date") else None,v.get("skipped",False)) for v in values))


class PostgresCreditCardRepository:
    FIELDS="id,name,credit_limit_cents,closing_day,due_day,payment_account_id,active"
    def __init__(self,uow):self.uow=uow
    def list_all(self):
        with self.uow.cursor() as c:c.execute(f"SELECT {self.FIELDS} FROM credit_cards ORDER BY name");return [self._domain(r) for r in c.fetchall()]
    def get(self,item_id):
        with self.uow.cursor() as c:c.execute(f"SELECT {self.FIELDS} FROM credit_cards WHERE id=%s",(item_id,));r=c.fetchone();return self._domain(r) if r else None
    def save(self,i):
        with self.uow.cursor() as c:c.execute("""INSERT INTO credit_cards VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,credit_limit_cents=EXCLUDED.credit_limit_cents,closing_day=EXCLUDED.closing_day,due_day=EXCLUDED.due_day,payment_account_id=EXCLUDED.payment_account_id,active=EXCLUDED.active""",(i.id,i.name,_cents(i.credit_limit),i.closing_day,i.due_day,i.payment_account_id,i.active))
        return i
    def delete(self,item_id):
        with self.uow.cursor() as c:c.execute("DELETE FROM credit_cards WHERE id=%s",(item_id,));return c.rowcount>0
    @staticmethod
    def _domain(r):return CreditCard(r[0],r[1],Money.from_value(Decimal(r[2])/100),r[3],r[4],r[5],r[6])


class PostgresCardPurchaseRepository:
    FIELDS="id,card_id,category_id,description,purchase_date,total_amount_cents,installments"
    def __init__(self,uow):self.uow=uow
    def list_all(self):
        with self.uow.cursor() as c:c.execute(f"SELECT {self.FIELDS} FROM card_purchases ORDER BY purchase_date DESC");return [self._domain(r) for r in c.fetchall()]
    def get(self,item_id):
        with self.uow.cursor() as c:c.execute(f"SELECT {self.FIELDS} FROM card_purchases WHERE id=%s",(item_id,));r=c.fetchone();return self._domain(r) if r else None
    def save(self,i):
        with self.uow.cursor() as c:c.execute("""INSERT INTO card_purchases VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET card_id=EXCLUDED.card_id,category_id=EXCLUDED.category_id,description=EXCLUDED.description,purchase_date=EXCLUDED.purchase_date,total_amount_cents=EXCLUDED.total_amount_cents,installments=EXCLUDED.installments""",(i.id,i.card_id,i.category_id,i.description,i.purchase_date,_cents(i.total_amount),i.installments))
        return i
    def delete(self,item_id):
        with self.uow.cursor() as c:c.execute("DELETE FROM card_purchases WHERE id=%s",(item_id,));return c.rowcount>0
    @staticmethod
    def _domain(r):return CardPurchase(r[0],r[1],r[2],r[3],r[4],Money.from_value(Decimal(r[5])/100),r[6])


class PostgresCardInstallmentRepository:
    FIELDS="id,purchase_id,card_id,category_id,description,amount_cents,number,total,invoice_month"
    def __init__(self,uow):self.uow=uow
    def list_by_card(self,card_id):
        with self.uow.cursor() as c:c.execute(f"SELECT {self.FIELDS} FROM card_installments WHERE card_id=%s ORDER BY invoice_month,number",(card_id,));return [self._domain(r) for r in c.fetchall()]
    def list_by_invoice(self,card_id,month):
        with self.uow.cursor() as c:c.execute(f"SELECT {self.FIELDS} FROM card_installments WHERE card_id=%s AND invoice_month=%s ORDER BY number",(card_id,month));return [self._domain(r) for r in c.fetchall()]
    def save_all(self,items):
        if not items:return []
        with self.uow.cursor() as c:c.executemany("""INSERT INTO card_installments VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET purchase_id=EXCLUDED.purchase_id,card_id=EXCLUDED.card_id,category_id=EXCLUDED.category_id,description=EXCLUDED.description,amount_cents=EXCLUDED.amount_cents,number=EXCLUDED.number,total=EXCLUDED.total,invoice_month=EXCLUDED.invoice_month""",[(i.id,i.purchase_id,i.card_id,i.category_id,i.description,_cents(i.amount),i.number,i.total,i.invoice_month) for i in items])
        return items
    def delete_by_purchase(self,item_id):
        with self.uow.cursor() as c:c.execute("DELETE FROM card_installments WHERE purchase_id=%s",(item_id,));return c.rowcount
    @staticmethod
    def _domain(r):return CardInstallment(r[0],r[1],r[2],r[3],r[4],Money.from_value(Decimal(r[5])/100),r[6],r[7],r[8])


class PostgresCardInvoiceRepository:
    FIELDS="id,card_id,reference_month,closing_date,due_date,total_cents,status,paid_at,payment_transaction_id"
    def __init__(self,uow):self.uow=uow
    def list_by_card(self,card_id):
        with self.uow.cursor() as c:c.execute(f"SELECT {self.FIELDS} FROM card_invoices WHERE card_id=%s ORDER BY reference_month DESC",(card_id,));return [self._domain(r) for r in c.fetchall()]
    def get(self,card_id,month):
        with self.uow.cursor() as c:c.execute(f"SELECT {self.FIELDS} FROM card_invoices WHERE card_id=%s AND reference_month=%s",(card_id,month));r=c.fetchone();return self._domain(r) if r else None
    def save(self,i):
        with self.uow.cursor() as c:c.execute("""INSERT INTO card_invoices VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET total_cents=EXCLUDED.total_cents,status=EXCLUDED.status,paid_at=EXCLUDED.paid_at,payment_transaction_id=EXCLUDED.payment_transaction_id""",(i.id,i.card_id,i.reference_month,i.closing_date,i.due_date,_cents(i.total),i.status.value,i.paid_at,i.payment_transaction_id))
        return i
    @staticmethod
    def _domain(r):return CardInvoice(r[0],r[1],r[2],r[3],r[4],Money.from_value(Decimal(r[5])/100),InvoiceStatus(r[6]),r[7],r[8])
