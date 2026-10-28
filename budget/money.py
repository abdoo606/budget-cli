"""Money handling. Integer minor units only - floats must never touch accounting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "SAR": "SAR ", "AED": "AED ", "GBP": "£"}


@dataclass(slots=True, frozen=True, order=True)
class Money:
    minor: int  # e.g. cents
    currency: str = "USD"

    @classmethod
    def parse(cls, raw: str, currency: str = "USD") -> "Money":
        cleaned = raw.replace(",", "").strip()
        try:
            value = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation as exc:
            raise ValueError(f"not an amount: {raw!r}") from exc
        return cls(int(value * 100), currency)

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor + other.minor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor - other.minor, self.currency)

    def __mul__(self, factor: float | int) -> "Money":
        return Money(int(round(self.minor * factor)), self.currency)

    def _check(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError("can only combine Money with Money")
        if other.currency != self.currency:
            raise ValueError(f"currency mismatch: {self.currency} vs {other.currency}")

    @property
    def decimal(self) -> Decimal:
        return (Decimal(self.minor) / 100).quantize(Decimal("0.01"))

    def __str__(self) -> str:
        symbol = CURRENCY_SYMBOLS.get(self.currency, self.currency + " ")
        sign = "-" if self.minor < 0 else ""
        return f"{sign}{symbol}{abs(self.decimal):,.2f}"

    def __format__(self, spec: str) -> str:
        return str(self)

    def __neg__(self) -> "Money":
        return Money(-self.minor, self.currency)
