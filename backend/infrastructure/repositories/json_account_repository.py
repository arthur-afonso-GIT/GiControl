from collections.abc import Callable
from datetime import date

from backend.domain import Account, AccountType, Money


class JsonAccountRepository:
    """Adapter entre contas do domínio e a lista JSON legada."""

    def __init__(self, records: list[dict], persist: Callable[[], None]):
        self._records = records
        self._persist = persist

    def list_all(self) -> list[Account]:
        return [self._to_domain(record) for record in self._records]

    def get(self, account_id: str) -> Account | None:
        record = next((item for item in self._records if item["id"] == account_id), None)
        return self._to_domain(record) if record else None

    def save(self, account: Account) -> Account:
        record = self._to_record(account)
        for current in self._records:
            if current["id"] == account.id:
                current.clear()
                current.update(record)
                self._persist()
                return account

        self._records.append(record)
        self._persist()
        return account

    def delete(self, account_id: str) -> bool:
        original_size = len(self._records)
        self._records[:] = [item for item in self._records if item["id"] != account_id]
        deleted = len(self._records) != original_size
        if deleted:
            self._persist()
        return deleted

    @staticmethod
    def _to_domain(record: dict) -> Account:
        return Account(
            id=record["id"],
            name=record["name"],
            account_type=AccountType(record["type"]),
            balance=Money.from_value(record.get("balance", 0.0)),
            monthly_income=Money.from_value(record.get("monthly_income", 0.0)),
            income_day=record.get("income_day"),
            income_category_id=record.get("income_category_id"),
            income_start_date=date.fromisoformat(record["income_start_date"]) if record.get("income_start_date") else None,
        )

    @staticmethod
    def _to_record(account: Account) -> dict:
        record = {
            "id": account.id,
            "name": account.name,
            "type": account.account_type.value,
            "balance": float(account.balance.amount),
            "monthly_income": float(account.monthly_income.amount),
        }
        if account.income_day is not None:
            record.update({"income_day": account.income_day, "income_category_id": account.income_category_id,
                           "income_start_date": account.income_start_date.isoformat() if account.income_start_date else None})
        return record
