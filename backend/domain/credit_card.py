from dataclasses import dataclass
from datetime import date

from backend.domain.enums import InvoiceStatus
from backend.domain.money import Money


def _text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} é obrigatório")
    return normalized


@dataclass(frozen=True, slots=True)
class CreditCard:
    id: str
    name: str
    credit_limit: Money
    closing_day: int
    due_day: int
    payment_account_id: str
    active: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _text(self.id, "id"))
        object.__setattr__(self, "name", _text(self.name, "nome"))
        object.__setattr__(self, "payment_account_id", _text(self.payment_account_id, "conta de pagamento"))
        if self.credit_limit.amount <= 0:
            raise ValueError("Limite do cartão deve ser maior que zero")
        if not 1 <= self.closing_day <= 31 or not 1 <= self.due_day <= 31:
            raise ValueError("Fechamento e vencimento devem estar entre os dias 1 e 31")


@dataclass(frozen=True, slots=True)
class CardPurchase:
    id: str
    card_id: str
    category_id: str
    description: str
    purchase_date: date
    total_amount: Money
    installments: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _text(self.id, "id"))
        object.__setattr__(self, "card_id", _text(self.card_id, "cartão"))
        object.__setattr__(self, "category_id", _text(self.category_id, "categoria"))
        object.__setattr__(self, "description", _text(self.description, "descrição"))
        if self.total_amount.amount <= 0:
            raise ValueError("Valor da compra deve ser maior que zero")
        if not 1 <= self.installments <= 120:
            raise ValueError("Quantidade de parcelas deve estar entre 1 e 120")


@dataclass(frozen=True, slots=True)
class CardInstallment:
    id: str
    purchase_id: str
    card_id: str
    category_id: str
    description: str
    amount: Money
    number: int
    total: int
    invoice_month: date

    def __post_init__(self) -> None:
        if self.amount.amount <= 0:
            raise ValueError("Valor da parcela deve ser maior que zero")
        if not 1 <= self.number <= self.total:
            raise ValueError("Identificação de parcela inválida")
        if self.invoice_month.day != 1:
            raise ValueError("Mês da fatura deve usar o primeiro dia como referência")


@dataclass(frozen=True, slots=True)
class CardInvoice:
    id: str
    card_id: str
    reference_month: date
    closing_date: date
    due_date: date
    total: Money
    status: InvoiceStatus = InvoiceStatus.OPEN
    paid_at: date | None = None
    payment_transaction_id: str | None = None

    def __post_init__(self) -> None:
        if self.reference_month.day != 1:
            raise ValueError("Mês da fatura deve usar o primeiro dia como referência")
        if self.due_date <= self.closing_date:
            raise ValueError("Vencimento deve ser posterior ao fechamento")
        if self.total.amount < 0:
            raise ValueError("Total da fatura não pode ser negativo")
        if self.status == InvoiceStatus.PAID and (not self.paid_at or not self.payment_transaction_id):
            raise ValueError("Fatura paga exige data e transação de pagamento")
        if self.status != InvoiceStatus.PAID and (self.paid_at or self.payment_transaction_id):
            raise ValueError("Somente faturas pagas possuem dados de pagamento")
