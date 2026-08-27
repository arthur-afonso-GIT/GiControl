from typing import Protocol

from backend.domain import Category


class CategoryRepository(Protocol):
    """Porta de persistência necessária pelos casos de uso de categorias."""

    def list_all(self) -> list[Category]: ...

    def get(self, category_id: str) -> Category | None: ...

    def save(self, category: Category) -> Category: ...

    def delete(self, category_id: str) -> bool: ...
