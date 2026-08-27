from dataclasses import dataclass, field
from datetime import date

from backend.domain.enums import AccountType, TransactionType
from backend.domain.money import Money


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} é obrigatório")
    return normalized


@dataclass(frozen=True, slots=True)
class Account:
    id: str
    name: str
    account_type: AccountType
    balance: Money = field(default_factory=Money.zero)
    monthly_income: Money = field(default_factory=Money.zero)
    income_day: int | None = None
    income_category_id: str | None = None
    income_start_date: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_text(self.id, "id"))
        object.__setattr__(self, "name", _required_text(self.name, "nome"))
        if self.monthly_income.amount < 0:
            raise ValueError("Renda mensal não pode ser negativa")
        if self.income_day is not None and not 1 <= self.income_day <= 31:
            raise ValueError("Dia de recebimento deve estar entre 1 e 31")
        if self.monthly_income.amount > 0 and self.income_day is not None and not self.income_category_id:
            raise ValueError("Categoria da renda prevista é obrigatória")


@dataclass(frozen=True, slots=True)
class Category:
    id: str
    name: str
    category_type: TransactionType
    monthly_limit: Money = field(default_factory=Money.zero)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_text(self.id, "id"))
        object.__setattr__(self, "name", _required_text(self.name, "nome"))
        if self.monthly_limit.amount < 0:
            raise ValueError("Limite mensal não pode ser negativo")
        if self.category_type == TransactionType.INCOME and self.monthly_limit.amount != 0:
            raise ValueError("Categorias de receita não possuem limite mensal")


@dataclass(frozen=True, slots=True)
class Transaction:
    id: str
    amount: Money
    date: date
    category_id: str
    account_id: str
    description: str
    transaction_type: TransactionType
    is_fixed: bool = False
    installment_group_id: str | None = None
    installment_number: int = 1
    installment_total: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_text(self.id, "id"))
        object.__setattr__(self, "category_id", _required_text(self.category_id, "category_id"))
        object.__setattr__(self, "account_id", _required_text(self.account_id, "account_id"))
        object.__setattr__(self, "description", _required_text(self.description, "descrição"))
        if self.amount.amount <= 0:
            raise ValueError("Valor da transação deve ser maior que zero")
        if self.installment_total < 1 or not 1 <= self.installment_number <= self.installment_total:
            raise ValueError("Identificação de parcela inválida")
        if self.installment_total > 1 and not self.installment_group_id:
            raise ValueError("Parcelas múltiplas exigem um identificador de série")


@dataclass(frozen=True, slots=True)
class OccurrenceException:
    month: str
    due_date: date | None = None
    skipped: bool = False


@dataclass(frozen=True, slots=True)
class RecurringExpense:
    id: str
    name: str
    amount: Money
    account_id: str
    category_id: str
    due_day: int
    start_date: date
    end_date: date | None = None
    active: bool = True
    exceptions: tuple[OccurrenceException, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_text(self.id, "id"))
        object.__setattr__(self, "name", _required_text(self.name, "nome"))
        if self.amount.amount <= 0:
            raise ValueError("Valor da despesa deve ser maior que zero")
        if not 1 <= self.due_day <= 31:
            raise ValueError("Dia de vencimento deve estar entre 1 e 31")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Data final não pode ser anterior à inicial")
