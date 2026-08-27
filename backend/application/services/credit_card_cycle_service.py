import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from backend.domain import CardInstallment, CardPurchase, CreditCard, Money


@dataclass(frozen=True, slots=True)
class InvoiceCycle:
    reference_month: date
    closing_date: date
    due_date: date


class CreditCardCycleService:
    """Calcula ciclos e parcelas sem produzir lançamentos na conta bancária."""

    @classmethod
    def cycle_for_purchase(cls, card: CreditCard, purchase_date: date) -> InvoiceCycle:
        closing = cls._date(purchase_date.year, purchase_date.month, card.closing_day)
        if purchase_date > closing:
            closing = cls._date(*cls._next_month(closing.year, closing.month), card.closing_day)
        due_year, due_month = ((closing.year, closing.month) if card.due_day > card.closing_day
                               else cls._next_month(closing.year, closing.month))
        due = cls._date(due_year, due_month, card.due_day)
        return InvoiceCycle(date(due.year, due.month, 1), closing, due)

    @classmethod
    def installments_for(cls, card: CreditCard, purchase: CardPurchase) -> list[CardInstallment]:
        first_cycle = cls.cycle_for_purchase(card, purchase.purchase_date)
        total_cents = int(purchase.total_amount.amount * 100)
        base, remainder = divmod(total_cents, purchase.installments)
        result = []
        year, month = first_cycle.reference_month.year, first_cycle.reference_month.month
        for index in range(purchase.installments):
            cents = base + (1 if index < remainder else 0)
            result.append(CardInstallment(
                id=f"{purchase.id}:{index + 1}", purchase_id=purchase.id, card_id=card.id,
                category_id=purchase.category_id, description=purchase.description,
                amount=Money.from_value(Decimal(cents) / 100), number=index + 1,
                total=purchase.installments, invoice_month=date(year, month, 1),
            ))
            year, month = cls._next_month(year, month)
        return result

    @classmethod
    def cycle_for_reference(cls, card: CreditCard, reference_month: date) -> InvoiceCycle:
        due = cls._date(reference_month.year, reference_month.month, card.due_day)
        close_year, close_month = ((reference_month.year, reference_month.month)
                                   if card.due_day > card.closing_day
                                   else cls._previous_month(reference_month.year, reference_month.month))
        closing = cls._date(close_year, close_month, card.closing_day)
        return InvoiceCycle(date(reference_month.year, reference_month.month, 1), closing, due)

    @staticmethod
    def _next_month(year: int, month: int) -> tuple[int, int]:
        return (year + 1, 1) if month == 12 else (year, month + 1)

    @staticmethod
    def _previous_month(year: int, month: int) -> tuple[int, int]:
        return (year - 1, 12) if month == 1 else (year, month - 1)

    @staticmethod
    def _date(year: int, month: int, day: int) -> date:
        return date(year, month, min(day, calendar.monthrange(year, month)[1]))
