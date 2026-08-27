import calendar
from dataclasses import dataclass, replace
from datetime import date
from uuid import uuid4

from backend.application.ports import UnitOfWork
from backend.domain import Money, OccurrenceException, RecurringExpense, Transaction, TransactionType


@dataclass(frozen=True, slots=True)
class SaveRecurringExpenseRequest:
    name: str
    amount: Money
    account_id: str
    category_id: str
    due_day: int
    start_date: date
    end_date: date | None = None
    active: bool = True


@dataclass(frozen=True, slots=True)
class ExpenseOccurrence:
    expense: RecurringExpense
    due_date: date
    confirmed: bool


class RecurringExpenseService:
    def __init__(self, unit_of_work: UnitOfWork): self._unit_of_work = unit_of_work

    def list_all(self): return self._unit_of_work.recurring_expenses.list_all()

    def save(self, request: SaveRecurringExpenseRequest, expense_id: str | None = None):
        current = self._unit_of_work.recurring_expenses.get(expense_id) if expense_id else None
        expense = RecurringExpense(id=expense_id or str(uuid4()), name=request.name, amount=request.amount,
            account_id=request.account_id, category_id=request.category_id, due_day=request.due_day,
            start_date=request.start_date, end_date=request.end_date, active=request.active,
            exceptions=current.exceptions if current else ())
        self._unit_of_work.recurring_expenses.save(expense); return expense

    def delete(self, expense_id: str): return self._unit_of_work.recurring_expenses.delete(expense_id)

    def list_month(self, reference: date):
        result = []
        for expense in self.list_all():
            due = date(reference.year, reference.month, min(expense.due_day, calendar.monthrange(reference.year, reference.month)[1]))
            exception = self._exception(expense, reference)
            if exception and exception.skipped: continue
            if exception and exception.due_date: due = exception.due_date
            if not expense.active or due < expense.start_date or (expense.end_date and due > expense.end_date): continue
            result.append(ExpenseOccurrence(expense, due, self._unit_of_work.transactions.get(self._transaction_id(expense.id, reference)) is not None))
        return sorted(result, key=lambda item: item.due_date)

    def confirm(self, expense_id: str, reference: date, today: date | None = None):
        expense = self._unit_of_work.recurring_expenses.get(expense_id)
        if expense is None: raise ValueError("Despesa prevista não encontrada")
        due = date(reference.year, reference.month, min(expense.due_day, calendar.monthrange(reference.year, reference.month)[1]))
        exception = self._exception(expense, reference)
        if exception and exception.skipped: raise ValueError("Despesa foi cancelada neste mês")
        if exception and exception.due_date: due = exception.due_date
        if not expense.active or due < expense.start_date or (expense.end_date and due > expense.end_date):
            raise ValueError("Despesa não está prevista para este mês")
        if due > (today or date.today()): raise ValueError("Despesa só pode ser confirmada na data prevista ou depois")
        transaction_id = self._transaction_id(expense_id, reference)
        existing = self._unit_of_work.transactions.get(transaction_id)
        if existing: return existing
        transaction = Transaction(id=transaction_id, amount=expense.amount, date=due, category_id=expense.category_id,
            account_id=expense.account_id, description=expense.name, transaction_type=TransactionType.EXPENSE, is_fixed=True)
        with self._unit_of_work as uow:
            account = uow.accounts.get(expense.account_id)
            if account is None: raise ValueError("Conta não encontrada")
            uow.accounts.save(replace(account, balance=account.balance - expense.amount))
            uow.transactions.save(transaction)
        return transaction

    @staticmethod
    def _transaction_id(expense_id: str, reference: date): return f"scheduled-expense:{expense_id}:{reference:%Y-%m}"

    def set_month_exception(self, expense_id: str, reference: date, due_date: date | None = None, skipped: bool = False):
        expense = self._unit_of_work.recurring_expenses.get(expense_id)
        if expense is None: raise ValueError("Despesa prevista não encontrada")
        original_due = date(reference.year, reference.month, min(expense.due_day, calendar.monthrange(reference.year, reference.month)[1]))
        if due_date and due_date < original_due:
            raise ValueError("A nova data deve ser posterior ao vencimento original")
        month = f"{reference:%Y-%m}"
        exceptions = tuple(item for item in expense.exceptions if item.month != month) + (OccurrenceException(month, due_date, skipped),)
        updated = replace(expense, exceptions=exceptions)
        self._unit_of_work.recurring_expenses.save(updated)
        return updated

    @staticmethod
    def _exception(expense: RecurringExpense, reference: date):
        month = f"{reference:%Y-%m}"
        return next((item for item in expense.exceptions if item.month == month), None)
