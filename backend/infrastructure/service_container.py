from pathlib import Path

from backend.application.ports import DataStore
from backend.application.services import (
    AccountService,
    BudgetQueryService,
    CategoryService,
    DashboardQueryService,
    ScheduledIncomeService,
    RecurringExpenseService,
    AgendaQueryService,
    TransactionService,
    CreditCardService,
    MonthlyReportService,
)
from backend.infrastructure.persistence_bootstrap import create_default_data_store
from backend.infrastructure.unit_of_work import JsonUnitOfWork
from backend.infrastructure.postgres_data_store import PostgresDataStore
from backend.infrastructure.postgres_unit_of_work import PostgresUnitOfWork


class ServiceContainer:
    """Compõe portas, adaptadores e casos de uso para qualquer interface externa."""

    def __init__(self, storage: DataStore):
        self.storage = storage
        self.data = storage.load()
        self.unit_of_work = (PostgresUnitOfWork(storage.database_url) if isinstance(storage, PostgresDataStore)
            else JsonUnitOfWork(self.data, lambda: self.storage.save(self.data)))
        self.accounts = AccountService(self.unit_of_work)
        self.categories = CategoryService(self.unit_of_work)
        self.budgets = BudgetQueryService(self.unit_of_work)
        self.dashboard = DashboardQueryService(self.unit_of_work)
        self.scheduled_incomes = ScheduledIncomeService(self.unit_of_work)
        self.recurring_expenses = RecurringExpenseService(self.unit_of_work)
        self.agenda = AgendaQueryService(self.unit_of_work, self.scheduled_incomes, self.recurring_expenses)
        self.transactions = TransactionService(self.unit_of_work)
        self.credit_cards = CreditCardService(self.unit_of_work)
        self.reports = MonthlyReportService(self.unit_of_work)


def create_default_service_container(project_dir: str | Path) -> ServiceContainer:
    return ServiceContainer(create_default_data_store(project_dir))
