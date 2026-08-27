from typing import Protocol

from backend.domain import Account


class AccountRepository(Protocol):
    """Porta de persistência necessária pelos casos de uso de contas."""

    def list_all(self) -> list[Account]: ...

    def get(self, account_id: str) -> Account | None: ...

    def save(self, account: Account) -> Account: ...

    def delete(self, account_id: str) -> bool: ...
