import uuid
from dataclasses import dataclass

from backend.application.ports import UnitOfWork
from backend.domain import Category, Money, TransactionType


@dataclass(frozen=True, slots=True)
class SaveCategoryRequest:
    name: str
    category_type: TransactionType
    monthly_limit: Money


class CategoryService:
    """Centraliza os casos de uso e a unicidade lógica das categorias."""

    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    def create_or_update(self, request: SaveCategoryRequest) -> Category:
        normalized_name = request.name.strip()
        existing = next(
            (
                category
                for category in self._unit_of_work.categories.list_all()
                if category.name.lower() == normalized_name.lower()
                and category.category_type == request.category_type
            ),
            None,
        )
        category = Category(
            id=existing.id if existing else str(uuid.uuid4()),
            name=normalized_name,
            category_type=request.category_type,
            monthly_limit=request.monthly_limit,
        )
        self._unit_of_work.categories.save(category)
        return category

    def update(self, category_id: str, request: SaveCategoryRequest) -> Category | None:
        if self._unit_of_work.categories.get(category_id) is None:
            return None
        category = Category(
            id=category_id,
            name=request.name,
            category_type=request.category_type,
            monthly_limit=request.monthly_limit,
        )
        self._unit_of_work.categories.save(category)
        return category

    def delete(self, category_id: str) -> bool:
        self._unit_of_work.categories.delete(category_id)
        return True

    def list_all(self) -> list[Category]:
        return self._unit_of_work.categories.list_all()
