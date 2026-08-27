import uuid
from dataclasses import dataclass, replace
from datetime import date

from backend.application.ports import UnitOfWork
from backend.domain import Account, AccountType, Money


@dataclass(frozen=True, slots=True)
class CreateAccountRequest:
    name: str
    account_type: AccountType
    initial_balance: Money
    monthly_income: Money
    income_day: int | None = None
    income_category_id: str | None = None
    income_start_date: date | None = None


class AccountService:
    """Executa casos de uso de contas sem conhecer o formato de persistência."""

    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    def create(self, request: CreateAccountRequest) -> Account:
        account = Account(
            id=str(uuid.uuid4()),
            name=request.name,
            account_type=request.account_type,
            balance=request.initial_balance,
            monthly_income=request.monthly_income,
            income_day=request.income_day,
            income_category_id=request.income_category_id,
            income_start_date=request.income_start_date,
        )
        self._unit_of_work.accounts.save(account)
        return account

    def update_balance(self, account_id: str, balance: Money) -> Account | None:
        account = self._unit_of_work.accounts.get(account_id)
        if account is None:
            return None
        updated = replace(account, balance=balance)
        self._unit_of_work.accounts.save(updated)
        return updated

    def update_monthly_income(self, account_id: str, income: Money) -> Account | None:
        account = self._unit_of_work.accounts.get(account_id)
        if account is None:
            return None
        updated = replace(account, monthly_income=income)
        self._unit_of_work.accounts.save(updated)
        return updated

    def update_income_schedule(self, account_id: str, income: Money, income_day: int | None,
                               category_id: str | None, start_date: date | None) -> Account | None:
        account = self._unit_of_work.accounts.get(account_id)
        if account is None:
            return None
        updated = replace(account, monthly_income=income, income_day=income_day,
                          income_category_id=category_id, income_start_date=start_date)
        self._unit_of_work.accounts.save(updated)
        return updated

    def delete(self, account_id: str) -> bool:
        with self._unit_of_work as uow:
            if uow.accounts.get(account_id) is None:
                return True
            uow.transactions.delete_by_account(account_id)
            uow.accounts.delete(account_id)
        return True

    def list_all(self) -> list[Account]:
        return self._unit_of_work.accounts.list_all()
