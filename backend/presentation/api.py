from datetime import date
import csv
import io
import os
from pathlib import Path
from threading import RLock

from fastapi import FastAPI, HTTPException, Request, Response, status
import httpx
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.application.services import (
    CreateAccountRequest,
    CreateTransactionRequest,
    SaveCategoryRequest,
    SaveRecurringExpenseRequest,
    UpdateTransactionRequest,
    CreateCardPurchaseRequest,
    SaveCreditCardRequest,
)
from backend.domain import AccountType, Money, TransactionType
from backend.infrastructure import ServiceContainer, create_default_service_container
from backend.infrastructure.auth_context import current_user_email, current_user_id


class AccountCreate(BaseModel):
    name: str
    type: AccountType
    initial_balance: float = 0
    monthly_income: float = Field(default=0, ge=0)
    income_day: int | None = Field(default=None, ge=1, le=31)
    income_category_id: str | None = None
    income_start_date: date | None = None


class AccountValueUpdate(BaseModel):
    value: float


class AccountIncomeScheduleUpdate(BaseModel):
    monthly_income: float = Field(ge=0)
    income_day: int | None = Field(default=None, ge=1, le=31)
    income_category_id: str | None = None
    income_start_date: date | None = None


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


class RecurringExpenseWrite(BaseModel):
    name: str
    amount: float = Field(gt=0)
    account_id: str
    category_id: str
    due_day: int = Field(ge=1, le=31)
    start_date: date
    end_date: date | None = None
    active: bool = True


class OccurrenceChange(BaseModel):
    due_date: date | None = None
    skipped: bool = False


class CreditCardWrite(BaseModel):
    name: str
    credit_limit: float = Field(gt=0)
    closing_day: int = Field(ge=1, le=31)
    due_day: int = Field(ge=1, le=31)
    payment_account_id: str
    active: bool = True


class CardPurchaseWrite(BaseModel):
    category_id: str
    description: str
    purchase_date: date
    total_amount: float = Field(gt=0)
    installments: int = Field(default=1, ge=1, le=120)


class CardInvoicePayment(BaseModel):
    paid_at: date | None = None


def create_api(container: ServiceContainer | None = None) -> FastAPI:
    services = container or create_default_service_container(
        Path(__file__).resolve().parents[2]
    )
    lock = RLock()
    api = FastAPI(title="GiControl API", version="1.0.0")

    @api.middleware("http")
    async def authenticate(request: Request, call_next):
        auth_default = "true" if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY") else "false"
        required = os.getenv("AUTH_REQUIRED", auth_default).lower() in {"1", "true", "yes"}
        if not required or request.url.path in {"/health", "/config", "/api/health", "/api/config", "/docs", "/openapi.json"}:
            return await call_next(request)
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail":"Autenticação necessária"})
        supabase_url, anon_key = os.getenv("SUPABASE_URL", "").rstrip("/"), os.getenv("SUPABASE_ANON_KEY", "")
        if not supabase_url or not anon_key:
            return JSONResponse(status_code=503, content={"detail":"Supabase Auth não está configurado no servidor"})
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                auth_response = await client.get(f"{supabase_url}/auth/v1/user", headers={
                    "Authorization":authorization, "apikey":anon_key})
            if auth_response.status_code != 200:
                return JSONResponse(status_code=401, content={"detail":"Sessão inválida ou expirada"})
            user = auth_response.json()
        except httpx.HTTPError:
            return JSONResponse(status_code=503, content={"detail":"Não foi possível validar a sessão"})
        id_token=current_user_id.set(user["id"]);email_token=current_user_email.set(user.get("email"))
        try:return await call_next(request)
        finally:current_user_id.reset(id_token);current_user_email.reset(email_token)

    @api.exception_handler(ValueError)
    async def value_error_handler(_request, exception: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exception)})

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.get("/config")
    def public_config():
        auth_default = "true" if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY") else "false"
        return {"supabase_url":os.getenv("SUPABASE_URL", ""),
                "supabase_anon_key":os.getenv("SUPABASE_ANON_KEY", ""),
                "auth_required":os.getenv("AUTH_REQUIRED", auth_default).lower() in {"1", "true", "yes"}}

    @api.get("/me")
    def me():
        return {"id":current_user_id.get(),"email":current_user_email.get()}

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
                income_day=payload.income_day, income_category_id=payload.income_category_id,
                income_start_date=payload.income_start_date,
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

    @api.put("/accounts/{account_id}/income-schedule")
    def update_account_income_schedule(account_id: str, payload: AccountIncomeScheduleUpdate):
        with lock:
            account = services.accounts.update_income_schedule(account_id, Money.from_value(payload.monthly_income),
                payload.income_day, payload.income_category_id, payload.income_start_date)
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

    @api.get("/reports/monthly")
    def monthly_report(month: str | None = None):
        with lock:
            return _monthly_report(services.reports.get_month(_month_reference(month)))

    @api.get("/reports/monthly.csv")
    def monthly_report_csv(month: str | None = None):
        with lock:
            report = services.reports.get_month(_month_reference(month))
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["GiControl - Relatório mensal", f"{report.reference_month:%m/%Y}"])
        writer.writerow(["Receitas", f"{report.income.amount:.2f}"])
        writer.writerow(["Despesas em contas", f"{report.bank_expenses.amount:.2f}"])
        writer.writerow(["Despesas em cartões", f"{report.card_expenses.amount:.2f}"])
        writer.writerow(["Resultado", f"{report.result.amount:.2f}"])
        writer.writerow([])
        writer.writerow(["Categoria", "Total"])
        for item in report.categories:
            writer.writerow([item.category_name, f"{item.total.amount:.2f}"])
        filename = f"gicontrol-{report.reference_month:%Y-%m}.csv"
        return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    @api.get("/scheduled-incomes")
    def scheduled_incomes(month: str | None = None):
        reference = _month_reference(month)
        with lock:
            return [{"account_id": item.account_id, "account_name": item.account_name,
                     "amount": float(item.amount.amount), "due_date": item.due_date.isoformat(),
                     "category_id": item.category_id, "confirmed": item.confirmed}
                    for item in services.scheduled_incomes.list_month(reference)]

    @api.post("/scheduled-incomes/{account_id}/{month}/confirm")
    def confirm_scheduled_income(account_id: str, month: str):
        reference = _month_reference(month)
        with lock:
            return _transaction(services.scheduled_incomes.confirm(account_id, reference))

    @api.get("/recurring-expenses")
    def list_recurring_expenses():
        with lock: return [_recurring_expense(item) for item in services.recurring_expenses.list_all()]

    @api.post("/recurring-expenses", status_code=status.HTTP_201_CREATED)
    def create_recurring_expense(payload: RecurringExpenseWrite):
        with lock: return _recurring_expense(services.recurring_expenses.save(_recurring_expense_request(payload)))

    @api.put("/recurring-expenses/{expense_id}")
    def update_recurring_expense(expense_id: str, payload: RecurringExpenseWrite):
        with lock: return _recurring_expense(services.recurring_expenses.save(_recurring_expense_request(payload), expense_id))

    @api.delete("/recurring-expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_recurring_expense(expense_id: str):
        with lock:
            if not services.recurring_expenses.delete(expense_id): raise HTTPException(status_code=404, detail="Despesa prevista não encontrada")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @api.get("/expense-occurrences")
    def expense_occurrences(month: str | None = None):
        reference = _month_reference(month)
        with lock: return [{**_recurring_expense(item.expense), "due_date": item.due_date.isoformat(), "confirmed": item.confirmed}
                           for item in services.recurring_expenses.list_month(reference)]

    @api.get("/agenda-summary")
    def agenda_summary(month: str | None = None):
        with lock:
            item = services.agenda.get_summary(_month_reference(month))
            return {"current_balance": float(item.current_balance.amount),
                    "pending_income": float(item.pending_income.amount),
                    "pending_expense": float(item.pending_expense.amount),
                    "projected_balance": float(item.projected_balance.amount),
                    "overdue_count": item.overdue_count}

    @api.get("/dashboard-view")
    def dashboard_view(month: str | None = None):
        """Entrega a tela inicial em uma única autenticação e viagem HTTP."""
        reference = _month_reference(month)
        with lock:
            metrics = services.dashboard.get_metrics(reference)
            budget_items = services.budgets.get_month(reference)
            income_items = services.scheduled_incomes.list_month(reference)
            summary = services.agenda.get_summary(reference)
            expense_items = services.recurring_expenses.list_month(reference)
            return {
                "metrics": {
                    "current_balance": float(metrics.current_balance.amount),
                    "monthly_income": float(metrics.monthly_income.amount),
                    "monthly_expense": float(metrics.monthly_expense.amount),
                    "savings": float(metrics.savings.amount),
                    "recent_transactions": [_transaction(item) for item in metrics.recent_transactions],
                },
                "budgets": [{
                    "category_id": item.category_id, "category_name": item.category_name,
                    "limit": float(item.limit.amount), "spent": float(item.spent.amount),
                    "remaining": float(item.remaining.amount),
                    "usage_percentage": float(item.usage_percentage),
                } for item in budget_items],
                "scheduled_incomes": [{
                    "account_id": item.account_id, "account_name": item.account_name,
                    "amount": float(item.amount.amount), "due_date": item.due_date.isoformat(),
                    "category_id": item.category_id, "confirmed": item.confirmed,
                } for item in income_items],
                "agenda": {
                    "current_balance": float(summary.current_balance.amount),
                    "pending_income": float(summary.pending_income.amount),
                    "pending_expense": float(summary.pending_expense.amount),
                    "projected_balance": float(summary.projected_balance.amount),
                    "overdue_count": summary.overdue_count,
                },
                "expenses": [{**_recurring_expense(item.expense),
                    "due_date": item.due_date.isoformat(), "confirmed": item.confirmed}
                    for item in expense_items],
            }

    @api.post("/expense-occurrences/{expense_id}/{month}/confirm")
    def confirm_expense_occurrence(expense_id: str, month: str):
        with lock: return _transaction(services.recurring_expenses.confirm(expense_id, _month_reference(month)))

    @api.put("/expense-occurrences/{expense_id}/{month}")
    def change_expense_occurrence(expense_id: str, month: str, payload: OccurrenceChange):
        reference = _month_reference(month)
        if payload.due_date and payload.due_date.strftime("%Y-%m") != month:
            raise HTTPException(status_code=422, detail="A nova data deve permanecer no mês da ocorrência")
        with lock:
            return _recurring_expense(services.recurring_expenses.set_month_exception(
                expense_id, reference, payload.due_date, payload.skipped))

    @api.get("/credit-cards")
    def list_credit_cards():
        with lock: return [_credit_card(item, services.credit_cards.available_limit(item.id)) for item in services.credit_cards.list_cards()]

    @api.post("/credit-cards", status_code=status.HTTP_201_CREATED)
    def create_credit_card(payload: CreditCardWrite):
        with lock: return _credit_card(services.credit_cards.save_card(_credit_card_request(payload)))

    @api.put("/credit-cards/{card_id}")
    def update_credit_card(card_id: str, payload: CreditCardWrite):
        with lock:
            if services.credit_cards.get_card(card_id) is None: raise HTTPException(status_code=404, detail="Cartão não encontrado")
            return _credit_card(services.credit_cards.save_card(_credit_card_request(payload), card_id))

    @api.get("/credit-cards/{card_id}/limit")
    def credit_card_limit(card_id: str):
        with lock:
            card=services.credit_cards.get_card(card_id)
            if card is None: raise HTTPException(status_code=404, detail="Cartão não encontrado")
            return {"credit_limit":float(card.credit_limit.amount),"available_limit":float(services.credit_cards.available_limit(card_id).amount)}

    @api.post("/credit-cards/{card_id}/purchases", status_code=status.HTTP_201_CREATED)
    def create_card_purchase(card_id: str, payload: CardPurchaseWrite):
        with lock:
            purchase, installments=services.credit_cards.create_purchase(CreateCardPurchaseRequest(card_id,payload.category_id,payload.description,payload.purchase_date,Money.from_value(payload.total_amount),payload.installments))
            return {"purchase":_card_purchase(purchase),"installments":[_card_installment(item) for item in installments]}

    @api.get("/credit-cards/{card_id}/invoices")
    def list_card_invoices(card_id: str):
        with lock:return [_card_invoice(item) for item in services.credit_cards.list_invoices(card_id)]

    @api.get("/credit-cards/{card_id}/invoices/{month}")
    def card_invoice_detail(card_id: str, month: str):
        with lock:
            invoices=services.credit_cards.list_invoices(card_id)
            invoice=next((item for item in invoices if f"{item.reference_month:%Y-%m}"==month),None)
            if invoice is None:raise HTTPException(status_code=404,detail="Fatura não encontrada")
            return {**_card_invoice(invoice),"installments":[_card_installment(item) for item in services.credit_cards.list_invoice_installments(card_id,month)]}

    @api.post("/credit-cards/{card_id}/invoices/{month}/close")
    def close_card_invoice(card_id: str, month: str):
        with lock:return _card_invoice(services.credit_cards.close_invoice(card_id, month))

    @api.post("/credit-cards/{card_id}/invoices/{month}/pay")
    def pay_card_invoice(card_id: str, month: str, payload: CardInvoicePayment):
        with lock:return _card_invoice(services.credit_cards.pay_invoice(card_id, month, payload.paid_at))

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


def _recurring_expense_request(payload: RecurringExpenseWrite) -> SaveRecurringExpenseRequest:
    return SaveRecurringExpenseRequest(name=payload.name, amount=Money.from_value(payload.amount),
        account_id=payload.account_id, category_id=payload.category_id, due_day=payload.due_day,
        start_date=payload.start_date, end_date=payload.end_date, active=payload.active)


def _recurring_expense(item) -> dict:
    return {"id": item.id, "name": item.name, "amount": float(item.amount.amount), "account_id": item.account_id,
            "category_id": item.category_id, "due_day": item.due_day, "start_date": item.start_date.isoformat(),
            "end_date": item.end_date.isoformat() if item.end_date else None, "active": item.active}


def _credit_card_request(payload: CreditCardWrite) -> SaveCreditCardRequest:
    return SaveCreditCardRequest(payload.name,Money.from_value(payload.credit_limit),payload.closing_day,payload.due_day,payload.payment_account_id,payload.active)


def _credit_card(item, available=None):
    result={"id":item.id,"name":item.name,"credit_limit":float(item.credit_limit.amount),"closing_day":item.closing_day,"due_day":item.due_day,"payment_account_id":item.payment_account_id,"active":item.active}
    if available is not None:result["available_limit"]=float(available.amount)
    return result


def _card_purchase(item):return {"id":item.id,"card_id":item.card_id,"category_id":item.category_id,"description":item.description,"purchase_date":item.purchase_date.isoformat(),"total_amount":float(item.total_amount.amount),"installments":item.installments}
def _card_installment(item):return {"id":item.id,"purchase_id":item.purchase_id,"card_id":item.card_id,"category_id":item.category_id,"description":item.description,"amount":float(item.amount.amount),"number":item.number,"total":item.total,"invoice_month":item.invoice_month.isoformat()}
def _card_invoice(item):return {"id":item.id,"card_id":item.card_id,"reference_month":item.reference_month.isoformat(),"closing_date":item.closing_date.isoformat(),"due_date":item.due_date.isoformat(),"total":float(item.total.amount),"status":item.status.value,"paid_at":item.paid_at.isoformat() if item.paid_at else None,"payment_transaction_id":item.payment_transaction_id}


def _monthly_report(item):
    return {"reference_month":item.reference_month.isoformat(),"income":float(item.income.amount),
        "bank_expenses":float(item.bank_expenses.amount),"card_expenses":float(item.card_expenses.amount),
        "total_expenses":float(item.total_expenses.amount),"result":float(item.result.amount),
        "categories":[{"category_id":row.category_id,"category_name":row.category_name,
            "total":float(row.total.amount)} for row in item.categories]}


def _account(account) -> dict:
    return {
        "id": account.id,
        "name": account.name,
        "type": account.account_type.value,
        "balance": float(account.balance.amount),
        "monthly_income": float(account.monthly_income.amount),
        "income_day": account.income_day,
        "income_category_id": account.income_category_id,
        "income_start_date": account.income_start_date.isoformat() if account.income_start_date else None,
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
