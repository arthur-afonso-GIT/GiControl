from dataclasses import dataclass
from datetime import date

from backend.application.ports import UnitOfWork
from backend.domain import InvoiceStatus, Money
from backend.application.services.recurring_expense_service import RecurringExpenseService
from backend.application.services.scheduled_income_service import ScheduledIncomeService


@dataclass(frozen=True, slots=True)
class AgendaSummary:
    current_balance: Money
    pending_income: Money
    pending_expense: Money
    projected_balance: Money
    overdue_count: int


class AgendaQueryService:
    def __init__(self, unit_of_work: UnitOfWork, incomes: ScheduledIncomeService,
                 expenses: RecurringExpenseService):
        self._unit_of_work = unit_of_work
        self._incomes = incomes
        self._expenses = expenses

    def get_summary(self, reference: date, today: date | None = None) -> AgendaSummary:
        current_day = today or date.today()
        current_balance = self._sum(account.balance for account in self._unit_of_work.accounts.list_all())
        incomes = [item for item in self._incomes.list_month(reference) if not item.confirmed]
        expenses = [item for item in self._expenses.list_month(reference) if not item.confirmed]
        pending_income = self._sum(item.amount for item in incomes)
        pending_expense = self._sum(item.expense.amount for item in expenses)
        card_invoices = [
            invoice
            for card in self._unit_of_work.credit_cards.list_all()
            for invoice in self._unit_of_work.card_invoices.list_by_card(card.id)
            if invoice.reference_month.year == reference.year
            and invoice.reference_month.month == reference.month
            and invoice.status != InvoiceStatus.PAID
        ]
        pending_expense += self._sum(invoice.total for invoice in card_invoices)
        return AgendaSummary(current_balance, pending_income, pending_expense,
            current_balance + pending_income - pending_expense,
            sum(1 for item in expenses if item.due_date < current_day)
            + sum(1 for invoice in card_invoices if invoice.due_date < current_day))

    @staticmethod
    def _sum(values):
        total = Money.zero()
        for value in values: total += value
        return total
