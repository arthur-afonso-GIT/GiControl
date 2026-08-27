from collections.abc import Callable

from backend.domain import Category, Money, TransactionType


class JsonCategoryRepository:
    """Adapter sobre a lista JSON legada compartilhada pelo FinanceManager."""

    def __init__(self, records: list[dict], persist: Callable[[], None]):
        self._records = records
        self._persist = persist

    def list_all(self) -> list[Category]:
        return [self._to_domain(record) for record in self._records]

    def get(self, category_id: str) -> Category | None:
        record = next((item for item in self._records if item["id"] == category_id), None)
        return self._to_domain(record) if record else None

    def save(self, category: Category) -> Category:
        record = self._to_record(category)
        for index, current in enumerate(self._records):
            if current["id"] == category.id:
                self._records[index] = record
                self._persist()
                return category

        self._records.append(record)
        self._persist()
        return category

    def delete(self, category_id: str) -> bool:
        original_size = len(self._records)
        self._records[:] = [item for item in self._records if item["id"] != category_id]
        deleted = len(self._records) != original_size
        if deleted:
            self._persist()
        return deleted

    @staticmethod
    def _to_domain(record: dict) -> Category:
        return Category(
            id=record["id"],
            name=record["name"],
            category_type=TransactionType(record["type"]),
            monthly_limit=Money.from_value(record.get("monthly_limit", 0.0)),
        )

    @staticmethod
    def _to_record(category: Category) -> dict:
        return {
            "id": category.id,
            "name": category.name,
            "type": category.category_type.value,
            "monthly_limit": float(category.monthly_limit.amount),
        }
