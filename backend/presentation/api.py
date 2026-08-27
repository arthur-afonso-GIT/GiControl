from datetime import date
from pathlib import Path
from threading import RLock

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.application.services import (
    CreateAccountRequest,
    CreateTransactionRequest,
    SaveCategoryRequest,
    UpdateTransactionRequest,
)
from backend.domain import AccountType, Money, TransactionType
from backend.infrastructure import ServiceContainer, create_default_service_container


class AccountCreate(BaseModel):
    name: str
    type: AccountType
    initial_balance: float = 0
    monthly_income: float = Field(default=0, ge=0)


class AccountValueUpdate(BaseModel):
    value: float


class CategoryWrite(BaseModel):
    name: str
    type: TransactionType
    monthly_limit: float = Field(default=0, ge=0)


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    category_id: str
    account_id: str
    description: str
    type: TransactionType
    date: date
    installments: int = Field(default=1, ge=1)
    is_fixed: bool = False


class TransactionUpdate(BaseModel):
    amount: float = Field(gt=0)
    category_id: str
    account_id: str
    description: str
    type: TransactionType
    date: date
    is_fixed: bool = False


def create_api(container: ServiceContainer | None = None) -> FastAPI:
    services = container or create_default_service_container(
        Path(__file__).resolve().parents[2]
    )
    lock = RLock()
    api = FastAPI(title="GiControl API", version="1.0.0")

    @api.exception_handler(ValueError)
    async def value_error_handler(_request, exception: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exception)})

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.get("/accounts")
    def list_accounts():
        with lock:
            return [_account(account) for account in services.accounts.list_all()]

    @api.post("/accounts", status_code=status.HTTP_201_CREATED)
    def create_account(payload: AccountCreate):
        with lock:
            account = services.accounts.create(CreateAccountRequest(
                name=payload.name,
                account_type=payload.type,
                initial_balance=Money.from_value(payload.initial_balance),
                monthly_income=Money.from_value(payload.monthly_income),
            ))
            return _account(account)

    @api.patch("/accounts/{account_id}/balance")
    def update_account_balance(account_id: str, payload: AccountValueUpdate):
        with lock:
            account = services.accounts.update_balance(
                account_id, Money.from_value(payload.value)
            )
            if account is None:
                raise HTTPException(status_code=404, detail="Conta não encontrada")
            return _account(account)

    @api.patch("/accounts/{account_id}/monthly-income")
    def update_account_income(account_id: str, payload: AccountValueUpdate):
        with lock:
            account = services.accounts.update_monthly_income(
                account_id, Money.from_value(payload.value)
            )
            if account is None:
                raise HTTPException(status_code=404, detail="Conta não encontrada")
            return _account(account)

    @api.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_account(account_id: str):
        with lock:
            services.accounts.delete(account_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @api.get("/categories")
    def list_categories():
        with lock:
            return [_category(category) for category in services.categories.list_all()]

    @api.post("/categories", status_code=status.HTTP_201_CREATED)
    def create_category(payload: CategoryWrite):
        with lock:
            category = services.categories.create_or_update(_category_request(payload))
            return _category(category)

    @api.put("/categories/{category_id}")
    def update_category(category_id: str, payload: CategoryWrite):
        with lock:
            category = services.categories.update(category_id, _category_request(payload))
            if category is None:
                raise HTTPException(status_code=404, detail="Categoria não encontrada")
            return _category(category)

    @api.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_category(category_id: str):
        with lock:
            services.categories.delete(category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @api.get("/transactions")
    def list_transactions():
        with lock:
            return [
                _transaction(transaction)
                for transaction in services.unit_of_work.transactions.list_all()
            ]

    @api.post("/transactions", status_code=status.HTTP_201_CREATED)
    def create_transaction(payload: TransactionCreate):
        with lock:
            transactions = services.transactions.create(CreateTransactionRequest(
                amount=Money.from_value(payload.amount),
                category_id=payload.category_id,
                account_id=payload.account_id,
                description=payload.description,
                transaction_type=payload.type,
                date=payload.date,
                installments=payload.installments,
                is_fixed=payload.is_fixed,
            ))
            return [_transaction(transaction) for transaction in transactions]

    @api.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_transaction(transaction_id: str):
        with lock:
            if not services.transactions.delete(transaction_id):
                raise HTTPException(status_code=404, detail="Transação não encontrada")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @api.put("/transactions/{transaction_id}")
    def update_transaction(transaction_id: str, payload: TransactionUpdate):
        with lock:
            transaction = services.transactions.update(transaction_id, UpdateTransactionRequest(
                amount=Money.from_value(payload.amount), category_id=payload.category_id,
                account_id=payload.account_id, description=payload.description,
                transaction_type=payload.type, date=payload.date, is_fixed=payload.is_fixed,
            ))
            if transaction is None:
                raise HTTPException(status_code=404, detail="Transação não encontrada")
            return _transaction(transaction)

    @api.delete("/transaction-series/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_transaction_series(group_id: str):
        with lock:
            if not services.transactions.delete_installment_series(group_id):
                raise HTTPException(status_code=404, detail="Série parcelada não encontrada")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @api.get("/dashboard")
    def dashboard(month: str | None = None):
        reference = _month_reference(month)
        with lock:
            metrics = services.dashboard.get_metrics(reference)
            return {
                "current_balance": float(metrics.current_balance.amount),
                "monthly_income": float(metrics.monthly_income.amount),
                "monthly_expense": float(metrics.monthly_expense.amount),
                "savings": float(metrics.savings.amount),
                "recent_transactions": [
                    _transaction(transaction)
                    for transaction in metrics.recent_transactions
                ],
            }

    @api.get("/budgets")
    def budgets(month: str | None = None):
        reference = _month_reference(month)
        with lock:
            return [{
                "category_id": item.category_id,
                "category_name": item.category_name,
                "limit": float(item.limit.amount),
                "spent": float(item.spent.amount),
                "remaining": float(item.remaining.amount),
                "usage_percentage": float(item.usage_percentage),
            } for item in services.budgets.get_month(reference)]

    return api


def _month_reference(month: str | None) -> date:
    try:
        return date.fromisoformat(f"{month}-01") if month else date.today()
    except ValueError as exception:
        raise HTTPException(status_code=422, detail="Mês deve usar o formato AAAA-MM") from exception


def _category_request(payload: CategoryWrite) -> SaveCategoryRequest:
    return SaveCategoryRequest(
        name=payload.name,
        category_type=payload.type,
        monthly_limit=Money.from_value(payload.monthly_limit),
    )


def _account(account) -> dict:
    return {
        "id": account.id,
        "name": account.name,
        "type": account.account_type.value,
        "balance": float(account.balance.amount),
        "monthly_income": float(account.monthly_income.amount),
    }


def _category(category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "type": category.category_type.value,
        "monthly_limit": float(category.monthly_limit.amount),
    }


def _transaction(transaction) -> dict:
    return {
        "id": transaction.id,
        "amount": float(transaction.amount.amount),
        "date": transaction.date.isoformat(),
        "category_id": transaction.category_id,
        "account_id": transaction.account_id,
        "description": transaction.description,
        "type": transaction.transaction_type.value,
        "is_fixed": transaction.is_fixed,
        "installment_group_id": transaction.installment_group_id,
        "installment_number": transaction.installment_number,
        "installment_total": transaction.installment_total,
    }


api = create_api()
