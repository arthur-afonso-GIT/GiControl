from types import TracebackType
from typing import Protocol, Self

from backend.application.ports.account_repository import AccountRepository
from backend.application.ports.category_repository import CategoryRepository
from backend.application.ports.transaction_repository import TransactionRepository
from backend.application.ports.recurring_expense_repository import RecurringExpenseRepository
from backend.application.ports.credit_card_repository import CardInstallmentRepository, CardInvoiceRepository, CardPurchaseRepository, CreditCardRepository


class UnitOfWork(Protocol):
    accounts: AccountRepository
    categories: CategoryRepository
    transactions: TransactionRepository
    recurring_expenses: RecurringExpenseRepository
    credit_cards: CreditCardRepository
    card_purchases: CardPurchaseRepository
    card_installments: CardInstallmentRepository
    card_invoices: CardInvoiceRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool: ...
