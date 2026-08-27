from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from typing import TypeAlias


MoneyInput: TypeAlias = Decimal | int | float | str
CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """Valor monetário em BRL com precisão decimal de centavos."""

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        normalized = Decimal(str(self.amount)).quantize(CENT, rounding=ROUND_HALF_EVEN)
        object.__setattr__(self, "amount", normalized)
        if self.currency != "BRL":
            raise ValueError("Apenas valores em BRL são suportados nesta fase")

    @classmethod
    def from_value(cls, value: MoneyInput) -> Money:
        return cls(Decimal(str(value)))

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal("0"))

    def __add__(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def _ensure_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError("Não é possível operar valores de moedas diferentes")
