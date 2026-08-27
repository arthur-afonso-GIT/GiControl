from dataclasses import dataclass
from datetime import date

from backend.application.ports import UnitOfWork
from backend.domain import CARD_INVOICE_PAYMENT_CATEGORY, Money, TransactionType


@dataclass(frozen=True, slots=True)
class CategoryExpenseReport:
    category_id: str
    category_name: str
    total: Money


@dataclass(frozen=True, slots=True)
class MonthlyReport:
    reference_month: date
    income: Money
    bank_expenses: Money
    card_expenses: Money
    total_expenses: Money
    result: Money
    categories: list[CategoryExpenseReport]


class MonthlyReportService:
    """Consolida competência mensal sem contar a liquidação do cartão duas vezes."""

    def __init__(self, unit_of_work: UnitOfWork): self.uow = unit_of_work

    def get_month(self, reference: date) -> MonthlyReport:
        month = date(reference.year, reference.month, 1)
        transactions = [item for item in self.uow.transactions.list_all()
            if item.date.year == month.year and item.date.month == month.month
            and item.category_id != CARD_INVOICE_PAYMENT_CATEGORY]
        installments = [item for card in self.uow.credit_cards.list_all()
            for item in self.uow.card_installments.list_by_invoice(card.id, month.isoformat())]
        income = self._sum(item.amount for item in transactions if item.transaction_type == TransactionType.INCOME)
        bank_expenses = self._sum(item.amount for item in transactions if item.transaction_type == TransactionType.EXPENSE)
        card_expenses = self._sum(item.amount for item in installments)
        category_totals: dict[str, Money] = {}
        for item in transactions:
            if item.transaction_type == TransactionType.EXPENSE:
                category_totals[item.category_id] = category_totals.get(item.category_id, Money.zero()) + item.amount
        for item in installments:
            category_totals[item.category_id] = category_totals.get(item.category_id, Money.zero()) + item.amount
        names = {item.id:item.name for item in self.uow.categories.list_all()}
        categories = sorted((CategoryExpenseReport(identifier, names.get(identifier, "Sem categoria"), total)
            for identifier,total in category_totals.items()), key=lambda item:item.total.amount, reverse=True)
        total_expenses = bank_expenses + card_expenses
        return MonthlyReport(month, income, bank_expenses, card_expenses, total_expenses,
            income - total_expenses, categories)

    @staticmethod
    def _sum(values):
        total=Money.zero()
        for value in values:total+=value
        return total
