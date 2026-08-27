from dataclasses import dataclass
from datetime import date

from backend.application.ports import UnitOfWork
from backend.domain import CARD_INVOICE_PAYMENT_CATEGORY, Money, Transaction, TransactionType


@dataclass(frozen=True, slots=True)
class DashboardMetrics:
    current_balance: Money
    monthly_income: Money
    monthly_expense: Money
    savings: Money
    recent_transactions: list[Transaction]


class DashboardQueryService:
    """Calcula a visão consolidada sem depender de dicionários das views."""

    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    def get_metrics(self, as_of: date | None = None) -> DashboardMetrics:
        reference = as_of or date.today()
        accounts = self._unit_of_work.accounts.list_all()
        transactions = self._unit_of_work.transactions.list_all()

        current_balance = self._sum(account.balance for account in accounts)
        expected_income = self._sum(account.monthly_income for account in accounts)
        current_transactions = [
            transaction
            for transaction in transactions
            if transaction.date.year == reference.year
            and transaction.date.month == reference.month
            and transaction.category_id != CARD_INVOICE_PAYMENT_CATEGORY
        ]
        real_income = self._sum(
            transaction.amount
            for transaction in current_transactions
            if transaction.transaction_type == TransactionType.INCOME
        )
        monthly_expense = self._sum(
            transaction.amount
            for transaction in current_transactions
            if transaction.transaction_type == TransactionType.EXPENSE
        )
        card_expense = self._sum(
            installment.amount
            for card in self._unit_of_work.credit_cards.list_all()
            for installment in self._unit_of_work.card_installments.list_by_invoice(
                card.id, date(reference.year, reference.month, 1).isoformat()
            )
        )
        monthly_expense += card_expense
        display_income = (
            real_income if real_income.amount > expected_income.amount else expected_income
        )
        return DashboardMetrics(
            current_balance=current_balance,
            monthly_income=display_income,
            monthly_expense=monthly_expense,
            savings=display_income - monthly_expense,
            recent_transactions=sorted(
                (item for item in transactions if item.category_id != CARD_INVOICE_PAYMENT_CATEGORY), key=lambda transaction: transaction.date, reverse=True
            )[:5],
        )

    @staticmethod
    def _sum(values) -> Money:
        total = Money.zero()
        for value in values:
            total += value
        return total
