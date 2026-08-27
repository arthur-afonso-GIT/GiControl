from collections.abc import Callable
from datetime import date

from backend.domain import Money, OccurrenceException, RecurringExpense


class JsonRecurringExpenseRepository:
    def __init__(self, records: list[dict], persist: Callable[[], None]):
        self._records = records
        self._persist = persist

    def list_all(self): return [self._to_domain(item) for item in self._records]
    def get(self, expense_id):
        item = next((item for item in self._records if item["id"] == expense_id), None)
        return self._to_domain(item) if item else None
    def save(self, expense):
        record = self._to_record(expense)
        current = next((item for item in self._records if item["id"] == expense.id), None)
        if current is None: self._records.append(record)
        else: current.clear(); current.update(record)
        self._persist(); return expense
    def delete(self, expense_id):
        before = len(self._records); self._records[:] = [item for item in self._records if item["id"] != expense_id]
        if len(self._records) != before: self._persist(); return True
        return False

    @staticmethod
    def _to_domain(item):
        return RecurringExpense(id=item["id"], name=item["name"], amount=Money.from_value(item["amount"]),
            account_id=item["account_id"], category_id=item["category_id"], due_day=item["due_day"],
            start_date=date.fromisoformat(item["start_date"]), end_date=date.fromisoformat(item["end_date"]) if item.get("end_date") else None,
            active=item.get("active", True), exceptions=tuple(OccurrenceException(month=value["month"],
                due_date=date.fromisoformat(value["due_date"]) if value.get("due_date") else None,
                skipped=value.get("skipped", False)) for value in item.get("exceptions", [])))
    @staticmethod
    def _to_record(item):
        return {"id": item.id, "name": item.name, "amount": float(item.amount.amount), "account_id": item.account_id,
            "category_id": item.category_id, "due_day": item.due_day, "start_date": item.start_date.isoformat(),
            "end_date": item.end_date.isoformat() if item.end_date else None, "active": item.active,
            "exceptions": [{"month": value.month, "due_date": value.due_date.isoformat() if value.due_date else None,
                            "skipped": value.skipped} for value in item.exceptions]}
