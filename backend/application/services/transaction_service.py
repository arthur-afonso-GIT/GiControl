from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

from backend.application.ports import UnitOfWork
from backend.domain import Money, Transaction, TransactionType


@dataclass(frozen=True, slots=True)
class CreateTransactionRequest:
    amount: Money
    category_id: str
    account_id: str
    description: str
    transaction_type: TransactionType
    date: date
    installments: int = 1
    is_fixed: bool = False


class TransactionService:
    """Coordena lançamentos e saldos dentro de uma unidade atômica."""

    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    def create(self, request: CreateTransactionRequest) -> list[Transaction]:
        if request.installments < 1:
            raise ValueError("A quantidade de parcelas deve ser maior que zero")

        transactions = self._build_installments(request)
        with self._unit_of_work as uow:
            account = uow.accounts.get(request.account_id)
            if account is None:
                raise ValueError("Conta não encontrada")

            total = Money.zero()
            for transaction in transactions:
                total += transaction.amount

            if request.transaction_type == TransactionType.INCOME:
                new_balance = account.balance + total
            else:
                new_balance = account.balance - total

            uow.accounts.save(replace(account, balance=new_balance))
            uow.transactions.save_all(transactions)

        return transactions

    def delete(self, transaction_id: str) -> bool:
        with self._unit_of_work as uow:
            transaction = uow.transactions.get(transaction_id)
            if transaction is None:
                return False

            account = uow.accounts.get(transaction.account_id)
            if account is not None:
                if transaction.transaction_type == TransactionType.INCOME:
                    new_balance = account.balance - transaction.amount
                else:
                    new_balance = account.balance + transaction.amount
                uow.accounts.save(replace(account, balance=new_balance))

            uow.transactions.delete(transaction_id)
            return True

    def delete_installment_series(self, group_id: str) -> int:
        with self._unit_of_work as uow:
            transactions = [
                transaction for transaction in uow.transactions.list_all()
                if transaction.installment_group_id == group_id
            ]
            if not transactions:
                return 0

            adjustments: dict[str, Money] = {}
            for transaction in transactions:
                signed_amount = transaction.amount if transaction.transaction_type == TransactionType.EXPENSE else Money.zero() - transaction.amount
                adjustments[transaction.account_id] = adjustments.get(transaction.account_id, Money.zero()) + signed_amount

            for account_id, adjustment in adjustments.items():
                account = uow.accounts.get(account_id)
                if account is not None:
                    uow.accounts.save(replace(account, balance=account.balance + adjustment))

            return uow.transactions.delete_by_installment_group(group_id)

    @staticmethod
    def _build_installments(request: CreateTransactionRequest) -> list[Transaction]:
        total_cents = int(request.amount.amount * 100)
        base_cents, remaining_cents = divmod(total_cents, request.installments)
        transactions = []
        installment_group_id = str(uuid4()) if request.installments > 1 else None

        for index in range(request.installments):
            installment_date = TransactionService._add_months(request.date, index)
            suffix = f" ({index + 1}/{request.installments})" if request.installments > 1 else ""
            installment_cents = base_cents + (1 if index < remaining_cents else 0)
            transactions.append(
                Transaction(
                    id=str(uuid4()),
                    amount=Money(Decimal(installment_cents) / 100),
                    date=installment_date,
                    category_id=request.category_id,
                    account_id=request.account_id,
                    description=f"{request.description}{suffix}",
                    transaction_type=request.transaction_type,
                    is_fixed=request.is_fixed,
                    installment_group_id=installment_group_id,
                    installment_number=index + 1,
                    installment_total=request.installments,
                )
            )

        return transactions

    @staticmethod
    def _add_months(base_date: date, months: int) -> date:
        year = base_date.year + (base_date.month + months - 1) // 12
        month = (base_date.month + months - 1) % 12 + 1
        days = [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ]
        return date(year, month, min(base_date.day, days[month - 1]))
