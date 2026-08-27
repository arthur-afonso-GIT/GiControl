from collections.abc import Callable
from datetime import date

from backend.domain import Money, Transaction, TransactionType


class JsonTransactionRepository:
    """Adapter entre lançamentos do domínio e a lista JSON legada."""

    def __init__(self, records: list[dict], persist: Callable[[], None]):
        self._records = records
        self._persist = persist

    def list_all(self) -> list[Transaction]:
        return [self._to_domain(record) for record in self._records]

    def get(self, transaction_id: str) -> Transaction | None:
        record = next((item for item in self._records if item["id"] == transaction_id), None)
        return self._to_domain(record) if record else None

    def save(self, transaction: Transaction) -> Transaction:
        self.save_all([transaction])
        return transaction

    def save_all(self, transactions: list[Transaction]) -> list[Transaction]:
        if not transactions:
            return []

        indexes = {record["id"]: index for index, record in enumerate(self._records)}
        for transaction in transactions:
            record = self._to_record(transaction)
            index = indexes.get(transaction.id)
            if index is None:
                indexes[transaction.id] = len(self._records)
                self._records.append(record)
            else:
                self._records[index].clear()
                self._records[index].update(record)

        self._persist()
        return transactions

    def delete(self, transaction_id: str) -> bool:
        return self._delete_matching(lambda item: item["id"] == transaction_id) > 0

    def delete_by_account(self, account_id: str) -> int:
        return self._delete_matching(lambda item: item["account_id"] == account_id)

    def delete_by_installment_group(self, group_id: str) -> int:
        return self._delete_matching(lambda item: item.get("installment_group_id") == group_id)

    def _delete_matching(self, predicate: Callable[[dict], bool]) -> int:
        original_size = len(self._records)
        self._records[:] = [item for item in self._records if not predicate(item)]
        deleted = original_size - len(self._records)
        if deleted:
            self._persist()
        return deleted

    @staticmethod
    def _to_domain(record: dict) -> Transaction:
        return Transaction(
            id=record["id"],
            amount=Money.from_value(record["amount"]),
            date=date.fromisoformat(record["date"]),
            category_id=record["category_id"],
            account_id=record["account_id"],
            description=record["description"],
            transaction_type=TransactionType(record["type"]),
            is_fixed=record.get("is_fixed", False),
            installment_group_id=record.get("installment_group_id"),
            installment_number=record.get("installment_number", 1),
            installment_total=record.get("installment_total", 1),
        )

    @staticmethod
    def _to_record(transaction: Transaction) -> dict:
        record = {
            "id": transaction.id,
            "amount": float(transaction.amount.amount),
            "date": transaction.date.isoformat(),
            "category_id": transaction.category_id,
            "account_id": transaction.account_id,
            "description": transaction.description,
            "type": transaction.transaction_type.value,
            "is_fixed": transaction.is_fixed,
        }
        if transaction.installment_group_id:
            record.update({
                "installment_group_id": transaction.installment_group_id,
                "installment_number": transaction.installment_number,
                "installment_total": transaction.installment_total,
            })
        return record
