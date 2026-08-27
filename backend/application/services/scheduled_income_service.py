import calendar
from dataclasses import dataclass, replace
from datetime import date

from backend.application.ports import UnitOfWork
from backend.domain import Money, Transaction, TransactionType


@dataclass(frozen=True, slots=True)
class ScheduledIncome:
    account_id: str
    account_name: str
    amount: Money
    due_date: date
    category_id: str
    confirmed: bool


class ScheduledIncomeService:
    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    def list_month(self, reference: date) -> list[ScheduledIncome]:
        result = []
        for account in self._unit_of_work.accounts.list_all():
            if not account.income_day or not account.income_category_id or account.monthly_income.amount <= 0:
                continue
            due = date(reference.year, reference.month, min(account.income_day, calendar.monthrange(reference.year, reference.month)[1]))
            if account.income_start_date and due < account.income_start_date:
                continue
            transaction_id = self._transaction_id(account.id, reference)
            result.append(ScheduledIncome(account.id, account.name, account.monthly_income, due,
                                          account.income_category_id,
                                          self._unit_of_work.transactions.get(transaction_id) is not None))
        return sorted(result, key=lambda item: item.due_date)

    def confirm(self, account_id: str, reference: date, today: date | None = None) -> Transaction:
        account = self._unit_of_work.accounts.get(account_id)
        if account is None or not account.income_day or not account.income_category_id or account.monthly_income.amount <= 0:
            raise ValueError("Conta não possui renda mensal programada")
        due = date(reference.year, reference.month, min(account.income_day, calendar.monthrange(reference.year, reference.month)[1]))
        if account.income_start_date and due < account.income_start_date:
            raise ValueError("Renda ainda não está vigente")
        if due > (today or date.today()):
            raise ValueError("Renda só pode ser confirmada na data prevista ou depois")
        transaction_id = self._transaction_id(account_id, reference)
        existing = self._unit_of_work.transactions.get(transaction_id)
        if existing:
            return existing
        transaction = Transaction(id=transaction_id, amount=account.monthly_income, date=due,
            category_id=account.income_category_id, account_id=account.id,
            description=f"Renda mensal — {account.name}", transaction_type=TransactionType.INCOME,
            is_fixed=True)
        with self._unit_of_work as uow:
            uow.accounts.save(replace(account, balance=account.balance + account.monthly_income))
            uow.transactions.save(transaction)
        return transaction

    @staticmethod
    def _transaction_id(account_id: str, reference: date) -> str:
        return f"scheduled-income:{account_id}:{reference:%Y-%m}"
