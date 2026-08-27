from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from backend.application.ports import UnitOfWork
from backend.domain import Money, TransactionType


@dataclass(frozen=True, slots=True)
class CategoryBudget:
    category_id: str
    category_name: str
    limit: Money
    spent: Money
    remaining: Money
    usage_percentage: Decimal


class BudgetQueryService:
    """Consolida o consumo mensal dos limites no lado da regra financeira."""

    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    def get_month(self, reference: date | None = None) -> list[CategoryBudget]:
        selected = reference or date.today()
        transactions = self._unit_of_work.transactions.list_all()
        budgets = []

        for category in self._unit_of_work.categories.list_all():
            if category.category_type != TransactionType.EXPENSE or category.monthly_limit.amount <= 0:
                continue
            spent = Money.zero()
            for transaction in transactions:
                if (
                    transaction.category_id == category.id
                    and transaction.transaction_type == TransactionType.EXPENSE
                    and transaction.date.year == selected.year
                    and transaction.date.month == selected.month
                ):
                    spent += transaction.amount
            remaining = category.monthly_limit - spent
            usage = spent.amount / category.monthly_limit.amount * Decimal("100")
            budgets.append(CategoryBudget(
                category_id=category.id,
                category_name=category.name,
                limit=category.monthly_limit,
                spent=spent,
                remaining=remaining,
                usage_percentage=usage.quantize(Decimal("0.01")),
            ))

        return sorted(budgets, key=lambda budget: budget.usage_percentage, reverse=True)
