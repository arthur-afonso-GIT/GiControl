from dataclasses import dataclass, replace
from datetime import date
from uuid import uuid4

from backend.application.ports import UnitOfWork
from backend.application.services.credit_card_cycle_service import CreditCardCycleService
from backend.domain import CARD_INVOICE_PAYMENT_CATEGORY, CardInvoice, CardPurchase, CreditCard, InvoiceStatus, Money, Transaction, TransactionType


@dataclass(frozen=True, slots=True)
class SaveCreditCardRequest:
    name: str
    credit_limit: Money
    closing_day: int
    due_day: int
    payment_account_id: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class CreateCardPurchaseRequest:
    card_id: str
    category_id: str
    description: str
    purchase_date: date
    total_amount: Money
    installments: int = 1


class CreditCardService:
    def __init__(self, unit_of_work: UnitOfWork): self.uow = unit_of_work

    def list_cards(self): return self.uow.credit_cards.list_all()
    def get_card(self, card_id): return self.uow.credit_cards.get(card_id)
    def save_card(self, request: SaveCreditCardRequest, card_id: str | None = None):
        if self.uow.accounts.get(request.payment_account_id) is None: raise ValueError("Conta de pagamento não encontrada")
        card = CreditCard(card_id or str(uuid4()), request.name, request.credit_limit, request.closing_day,
                          request.due_day, request.payment_account_id, request.active)
        return self.uow.credit_cards.save(card)

    def available_limit(self, card_id: str) -> Money:
        card = self._card(card_id)
        paid = {invoice.reference_month for invoice in self.uow.card_invoices.list_by_card(card_id)
                if invoice.status == InvoiceStatus.PAID}
        outstanding = sum((item.amount for item in self.uow.card_installments.list_by_card(card_id)
                           if item.invoice_month not in paid), Money.zero())
        return card.credit_limit - outstanding

    def create_purchase(self, request: CreateCardPurchaseRequest):
        card = self._card(request.card_id)
        if not card.active: raise ValueError("Cartão está inativo")
        if self.uow.categories.get(request.category_id) is None: raise ValueError("Categoria não encontrada")
        if request.total_amount.amount > self.available_limit(card.id).amount: raise ValueError("Limite insuficiente")
        purchase = CardPurchase(str(uuid4()), card.id, request.category_id, request.description,
                                request.purchase_date, request.total_amount, request.installments)
        installments = CreditCardCycleService.installments_for(card, purchase)
        for month in {item.invoice_month for item in installments}:
            existing = self.uow.card_invoices.get(card.id, month.isoformat())
            if existing is not None and existing.status != InvoiceStatus.OPEN:
                raise ValueError(f"A fatura de {month:%m/%Y} já está fechada")
        with self.uow as uow:
            uow.card_purchases.save(purchase)
            uow.card_installments.save_all(installments)
            for month in sorted({item.invoice_month for item in installments}):
                values = uow.card_installments.list_by_invoice(card.id, month.isoformat())
                total = sum((item.amount for item in values), Money.zero())
                cycle = CreditCardCycleService.cycle_for_reference(card, month)
                existing = uow.card_invoices.get(card.id, month.isoformat())
                invoice = CardInvoice(existing.id if existing else f"{card.id}:{month:%Y-%m}", card.id, month,
                    cycle.closing_date, cycle.due_date, total, existing.status if existing else InvoiceStatus.OPEN,
                    existing.paid_at if existing else None, existing.payment_transaction_id if existing else None)
                uow.card_invoices.save(invoice)
        return purchase, installments

    def list_invoices(self, card_id: str): self._card(card_id); return self.uow.card_invoices.list_by_card(card_id)
    def list_invoice_installments(self, card_id: str, month: str):
        self._card(card_id); return self.uow.card_installments.list_by_invoice(card_id, f"{month}-01")

    def close_invoice(self, card_id: str, month: str, as_of: date | None = None) -> CardInvoice:
        invoice = self._invoice(card_id, month)
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Fatura paga não pode ser fechada novamente")
        if invoice.status == InvoiceStatus.CLOSED:
            return invoice
        reference = as_of or date.today()
        if reference < invoice.closing_date:
            raise ValueError(f"A fatura só pode ser fechada a partir de {invoice.closing_date:%d/%m/%Y}")
        with self.uow as uow:
            return uow.card_invoices.save(replace(invoice, status=InvoiceStatus.CLOSED))

    def pay_invoice(self, card_id: str, month: str, paid_at: date | None = None) -> CardInvoice:
        invoice = self._invoice(card_id, month)
        if invoice.status == InvoiceStatus.PAID:
            return invoice
        if invoice.status != InvoiceStatus.CLOSED:
            raise ValueError("Feche a fatura antes de confirmar o pagamento")
        card = self._card(card_id)
        payment_date = paid_at or date.today()
        transaction_id = f"card-invoice-payment:{invoice.id}"
        with self.uow as uow:
            current = uow.card_invoices.get(card_id, invoice.reference_month.isoformat())
            if current is None:
                raise ValueError("Fatura não encontrada")
            if current.status == InvoiceStatus.PAID:
                return current
            account = uow.accounts.get(card.payment_account_id)
            if account is None:
                raise ValueError("Conta de pagamento não encontrada")
            payment = Transaction(transaction_id, current.total, payment_date,
                CARD_INVOICE_PAYMENT_CATEGORY, account.id, f"Pagamento da fatura {card.name} {month}",
                TransactionType.EXPENSE)
            uow.accounts.save(replace(account, balance=account.balance - current.total))
            uow.transactions.save(payment)
            return uow.card_invoices.save(replace(current, status=InvoiceStatus.PAID,
                paid_at=payment_date, payment_transaction_id=transaction_id))

    def _invoice(self, card_id: str, month: str) -> CardInvoice:
        self._card(card_id)
        try:
            date.fromisoformat(f"{month}-01")
        except ValueError as error:
            raise ValueError("Mês deve usar o formato AAAA-MM") from error
        invoice = self.uow.card_invoices.get(card_id, f"{month}-01")
        if invoice is None:
            raise ValueError("Fatura não encontrada")
        return invoice

    def _card(self, card_id):
        card=self.uow.credit_cards.get(card_id)
        if card is None: raise ValueError("Cartão não encontrado")
        return card
