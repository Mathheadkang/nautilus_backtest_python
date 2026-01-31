from __future__ import annotations


class _Identifier:
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError(f"{type(self).__name__} value must be non-empty")
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._value))

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self._value}')"

    def __str__(self) -> str:
        return self._value


class TraderId(_Identifier):
    pass


class StrategyId(_Identifier):
    pass


class InstrumentId(_Identifier):
    """Format: SYMBOL.VENUE"""

    def __init__(self, symbol: Symbol, venue: Venue) -> None:
        super().__init__(f"{symbol.value}.{venue.value}")
        self._symbol = symbol
        self._venue = venue

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def venue(self) -> Venue:
        return self._venue

    @classmethod
    def from_str(cls, value: str) -> InstrumentId:
        parts = value.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid InstrumentId format: '{value}', expected 'SYMBOL.VENUE'")
        return cls(Symbol(parts[0]), Venue(parts[1]))


class Venue(_Identifier):
    pass


class Symbol(_Identifier):
    pass


class AccountId(_Identifier):
    pass


class ClientOrderId(_Identifier):
    pass


class VenueOrderId(_Identifier):
    pass


class PositionId(_Identifier):
    pass


class TradeId(_Identifier):
    pass


class OrderListId(_Identifier):
    pass
