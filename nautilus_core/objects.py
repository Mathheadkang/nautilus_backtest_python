from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from nautilus_core.enums import CurrencyType


@dataclass(frozen=True)
class Currency:
    code: str
    precision: int
    currency_type: CurrencyType

    def __repr__(self) -> str:
        return f"Currency('{self.code}')"

    def __str__(self) -> str:
        return self.code


# Pre-defined currencies
USD = Currency("USD", 2, CurrencyType.FIAT)
EUR = Currency("EUR", 2, CurrencyType.FIAT)
GBP = Currency("GBP", 2, CurrencyType.FIAT)
JPY = Currency("JPY", 0, CurrencyType.FIAT)
BTC = Currency("BTC", 8, CurrencyType.CRYPTO)
ETH = Currency("ETH", 8, CurrencyType.CRYPTO)
USDT = Currency("USDT", 2, CurrencyType.CRYPTO)


class Price:
    __slots__ = ("_value", "_precision")

    def __init__(self, value: Decimal | str | float, precision: int) -> None:
        self._precision = precision
        d = Decimal(str(value))
        self._value = d.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)

    @property
    def value(self) -> Decimal:
        return self._value

    @property
    def precision(self) -> int:
        return self._precision

    def as_double(self) -> float:
        return float(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Price):
            return self._value == other._value
        if isinstance(other, (int, float, Decimal)):
            return self._value == Decimal(str(other))
        return NotImplemented

    def __lt__(self, other: Price | Decimal | float | int) -> bool:
        if isinstance(other, Price):
            return self._value < other._value
        return self._value < Decimal(str(other))

    def __le__(self, other: Price | Decimal | float | int) -> bool:
        if isinstance(other, Price):
            return self._value <= other._value
        return self._value <= Decimal(str(other))

    def __gt__(self, other: Price | Decimal | float | int) -> bool:
        if isinstance(other, Price):
            return self._value > other._value
        return self._value > Decimal(str(other))

    def __ge__(self, other: Price | Decimal | float | int) -> bool:
        if isinstance(other, Price):
            return self._value >= other._value
        return self._value >= Decimal(str(other))

    def __add__(self, other: Price | Decimal | float | int) -> Price:
        if isinstance(other, Price):
            return Price(self._value + other._value, max(self._precision, other._precision))
        return Price(self._value + Decimal(str(other)), self._precision)

    def __sub__(self, other: Price | Decimal | float | int) -> Price:
        if isinstance(other, Price):
            return Price(self._value - other._value, max(self._precision, other._precision))
        return Price(self._value - Decimal(str(other)), self._precision)

    def __mul__(self, other: Decimal | float | int) -> Price:
        return Price(self._value * Decimal(str(other)), self._precision)

    def __neg__(self) -> Price:
        return Price(-self._value, self._precision)

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"Price('{self._value}')"

    def __str__(self) -> str:
        return str(self._value)

    def __float__(self) -> float:
        return float(self._value)


class Quantity:
    __slots__ = ("_value", "_precision")

    def __init__(self, value: Decimal | str | float, precision: int) -> None:
        self._precision = precision
        d = Decimal(str(value))
        self._value = d.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)
        if self._value < 0:
            raise ValueError(f"Quantity value must be non-negative, got {self._value}")

    @property
    def value(self) -> Decimal:
        return self._value

    @property
    def precision(self) -> int:
        return self._precision

    def as_double(self) -> float:
        return float(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Quantity):
            return self._value == other._value
        if isinstance(other, (int, float, Decimal)):
            return self._value == Decimal(str(other))
        return NotImplemented

    def __lt__(self, other: Quantity | Decimal | float | int) -> bool:
        if isinstance(other, Quantity):
            return self._value < other._value
        return self._value < Decimal(str(other))

    def __le__(self, other: Quantity | Decimal | float | int) -> bool:
        if isinstance(other, Quantity):
            return self._value <= other._value
        return self._value <= Decimal(str(other))

    def __gt__(self, other: Quantity | Decimal | float | int) -> bool:
        if isinstance(other, Quantity):
            return self._value > other._value
        return self._value > Decimal(str(other))

    def __ge__(self, other: Quantity | Decimal | float | int) -> bool:
        if isinstance(other, Quantity):
            return self._value >= other._value
        return self._value >= Decimal(str(other))

    def __add__(self, other: Quantity | Decimal | float | int) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(self._value + other._value, max(self._precision, other._precision))
        return Quantity(self._value + Decimal(str(other)), self._precision)

    def __sub__(self, other: Quantity | Decimal | float | int) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(self._value - other._value, max(self._precision, other._precision))
        return Quantity(self._value - Decimal(str(other)), self._precision)

    def __mul__(self, other: Decimal | float | int) -> Quantity:
        return Quantity(self._value * Decimal(str(other)), self._precision)

    def __bool__(self) -> bool:
        return self._value > 0

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"Quantity('{self._value}')"

    def __str__(self) -> str:
        return str(self._value)

    def __float__(self) -> float:
        return float(self._value)


class Money:
    __slots__ = ("_amount", "_currency")

    def __init__(self, amount: Decimal | str | float, currency: Currency) -> None:
        self._currency = currency
        d = Decimal(str(amount))
        self._amount = d.quantize(Decimal(10) ** -currency.precision, rounding=ROUND_HALF_UP)

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def currency(self) -> Currency:
        return self._currency

    def as_double(self) -> float:
        return float(self._amount)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self._amount == other._amount and self._currency == other._currency
        return NotImplemented

    def __add__(self, other: Money) -> Money:
        if self._currency != other._currency:
            raise ValueError(f"Cannot add {self._currency} and {other._currency}")
        return Money(self._amount + other._amount, self._currency)

    def __sub__(self, other: Money) -> Money:
        if self._currency != other._currency:
            raise ValueError(f"Cannot subtract {other._currency} from {self._currency}")
        return Money(self._amount - other._amount, self._currency)

    def __neg__(self) -> Money:
        return Money(-self._amount, self._currency)

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))

    def __repr__(self) -> str:
        return f"Money({self._amount}, {self._currency.code})"

    def __str__(self) -> str:
        return f"{self._amount} {self._currency.code}"


@dataclass
class AccountBalance:
    total: Money
    locked: Money
    free: Money

    def __post_init__(self) -> None:
        if self.total.currency != self.locked.currency or self.total.currency != self.free.currency:
            raise ValueError("All balance components must be in the same currency")
