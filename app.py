from datetime import datetime
from pathlib import Path
from backend.application.ports import DataStore
from backend.application.services import (
    CreateAccountRequest,
    CreateTransactionRequest,
    SaveCategoryRequest,
)
from backend.domain import Account, AccountType, Category, Money, Transaction, TransactionType
from backend.infrastructure import ServiceContainer, create_default_data_store

class FinanceManager:
    def __init__(self, storage: DataStore | None = None):
        self.storage = storage or create_default_data_store(Path(__file__).resolve().parent)
        self._configure_services(ServiceContainer(self.storage))

    def _configure_services(self, container: ServiceContainer):
        """Expõe a composição compartilhada mantendo o contrato legado das views."""
        self.container = container
        self.data = container.data
        self.unit_of_work = container.unit_of_work
        self.category_repository = self.unit_of_work.categories
        self.account_repository = self.unit_of_work.accounts
        self.transaction_repository = self.unit_of_work.transactions
        self.account_service = container.accounts
        self.category_service = container.categories
        self.dashboard_query_service = container.dashboard
        self.transaction_service = container.transactions

    # =========================================================================
    # GESTÃO DE CONTAS / CARTEIRAS
    # =========================================================================
    def add_account(self, name: str, account_type: str, initial_balance: float, monthly_income: float = 0.0):
        """Cadastra uma nova conta bancária ou carteira física."""
        account = self.account_service.create(CreateAccountRequest(
            name=name,
            account_type=AccountType(account_type),
            initial_balance=Money.from_value(initial_balance),
            monthly_income=Money.from_value(monthly_income),
        ))
        return next(item for item in self.data["accounts"] if item["id"] == account.id)

    def update_account_balance(self, account_id: str, new_balance: float):
        """Altera diretamente o saldo atual de uma conta."""
        return self.account_service.update_balance(
            account_id, Money.from_value(new_balance)
        ) is not None

    def update_account_monthly_income(self, account_id: str, new_income: float):
        """Altera diretamente a renda mensal fixa prevista de uma conta específica."""
        return self.account_service.update_monthly_income(
            account_id, Money.from_value(new_income)
        ) is not None

    def delete_account(self, account_id: str):
        """Remove permanentemente uma conta e limpa seus lançamentos atrelados."""
        return self.account_service.delete(account_id)

    def get_accounts(self):
        """Retorna todas as contas injetando propriedades ausentes por retrocompatibilidade."""
        return [self._account_to_legacy(account) for account in self.account_service.list_all()]

    @staticmethod
    def _account_to_legacy(account: Account) -> dict:
        """Mantém o contrato de contas esperado pelas views PySide6."""
        return {
            "id": account.id,
            "name": account.name,
            "type": account.account_type.value,
            "balance": float(account.balance.amount),
            "monthly_income": float(account.monthly_income.amount),
        }

    # =========================================================================
    # GESTÃO DE CATEGORIAS (COM SUPORTE A METAS/LIMITES E EXCLUSÃO)
    # =========================================================================
    def add_category(self, name: str, category_type: str, monthly_limit: float = 0.0):
        """Adiciona uma nova categoria salvando o teto de gastos estipulado."""
        category = self.category_service.create_or_update(SaveCategoryRequest(
            name=name,
            category_type=TransactionType(category_type),
            monthly_limit=Money.from_value(monthly_limit),
        ))
        return self._category_to_legacy(category)

    def delete_category(self, category_id: str):
        """Remove permanentemente uma categoria da lista."""
        return self.category_service.delete(category_id)

    def update_category(self, category_id: str, name: str, category_type: str, monthly_limit: float = 0.0):
        """Atualiza uma categoria existente sem expor a persistência para a interface."""
        category = self.category_service.update(category_id, SaveCategoryRequest(
            name=name,
            category_type=TransactionType(category_type),
            monthly_limit=Money.from_value(monthly_limit),
        ))
        if category is None:
            return None
        return self._category_to_legacy(category)

    def get_categories(self):
        """Retorna a lista de categorias garantindo que o campo monthly_limit exista."""
        return [
            self._category_to_legacy(category)
            for category in self.category_service.list_all()
        ]

    @staticmethod
    def _category_to_legacy(category: Category) -> dict:
        """Mantém o contrato de dicionários esperado pelas views PySide6."""
        return {
            "id": category.id,
            "name": category.name,
            "type": category.category_type.value,
            "monthly_limit": float(category.monthly_limit.amount),
        }

    # =========================================================================
    # MOVIMENTAÇÕES FINANCEIRAS
    # =========================================================================
    def add_transaction(
        self,
        amount: float,
        category_id: str,
        account_id: str,
        description: str,
        transaction_type: str,
        date: str = None,
        installments: int = 1,
        is_fixed: bool = False,
    ):
        """Registra movimentações tratando divisões em parcelas mensais futuras automáticas."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        self.transaction_service.create(
            CreateTransactionRequest(
                amount=Money.from_value(amount),
                category_id=category_id,
                account_id=account_id,
                description=description,
                transaction_type=TransactionType(transaction_type),
                date=datetime.strptime(date, "%Y-%m-%d").date(),
                installments=installments,
                is_fixed=is_fixed,
            )
        )

    def delete_transaction(self, transaction_id: str):
        """Remove a transação e estorna/devolve o valor ao saldo da respectiva conta."""
        return self.transaction_service.delete(transaction_id)

    def get_transactions(self):
        """Retorna todas as transações gravadas."""
        return [
            self._transaction_to_legacy(transaction)
            for transaction in self.transaction_repository.list_all()
        ]

    @staticmethod
    def _transaction_to_legacy(transaction: Transaction) -> dict:
        """Mantém o contrato de transações esperado pelas views PySide6."""
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

    # =========================================================================
    # MOTOR DE MÉTRICAS DO DASHBOARD
    # =========================================================================
    def get_dashboard_metrics(self):
        """Calcula o balanço e a saúde financeira consolidada baseada no mês corrente."""
        metrics = self.dashboard_query_service.get_metrics()
        return {
            "current_balance": float(metrics.current_balance.amount),
            "monthly_income": float(metrics.monthly_income.amount),
            "monthly_expense": float(metrics.monthly_expense.amount),
            "savings": float(metrics.savings.amount),
            "recent_transactions": [
                self._transaction_to_legacy(transaction)
                for transaction in metrics.recent_transactions
            ],
        }
