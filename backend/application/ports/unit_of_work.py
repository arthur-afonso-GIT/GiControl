from types import TracebackType
from typing import Protocol, Self

from backend.application.ports.account_repository import AccountRepository
from backend.application.ports.category_repository import CategoryRepository
from backend.application.ports.transaction_repository import TransactionRepository


class UnitOfWork(Protocol):
    accounts: AccountRepository
    categories: CategoryRepository
    transactions: TransactionRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool: ...
