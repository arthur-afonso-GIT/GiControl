from typing import Protocol, runtime_checkable


@runtime_checkable
class DataStore(Protocol):
    """Porta transitória para carregar e salvar o estado legado da aplicação."""

    def load(self) -> dict: ...

    def save(self, data: dict) -> None: ...
