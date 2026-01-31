from __future__ import annotations

from decimal import Decimal

from nautilus_core.cache import Cache
from nautilus_core.enums import PositionSide
from nautilus_core.identifiers import InstrumentId, Venue
from nautilus_core.objects import Currency, Money, Price


class Portfolio:
    def __init__(self, cache: Cache) -> None:
        self._cache = cache

    def net_position(self, instrument_id: InstrumentId) -> Decimal:
        total = Decimal("0")
        for pos in self._cache.positions_open(instrument_id=instrument_id):
            total += pos.signed_qty
        return total

    def is_net_long(self, instrument_id: InstrumentId) -> bool:
        return self.net_position(instrument_id) > 0

    def is_net_short(self, instrument_id: InstrumentId) -> bool:
        return self.net_position(instrument_id) < 0

    def is_flat(self, instrument_id: InstrumentId) -> bool:
        return self.net_position(instrument_id) == 0

    def unrealized_pnl(self, instrument_id: InstrumentId, last_price: Price) -> Decimal:
        total = Decimal("0")
        for pos in self._cache.positions_open(instrument_id=instrument_id):
            total += pos.unrealized_pnl(last_price)
        return total

    def realized_pnl(self, instrument_id: InstrumentId) -> Decimal:
        total = Decimal("0")
        for pos in self._cache.positions(instrument_id=instrument_id):
            total += pos.realized_pnl
        return total

    def net_exposure(self, instrument_id: InstrumentId, last_price: Price) -> Decimal:
        total = Decimal("0")
        for pos in self._cache.positions_open(instrument_id=instrument_id):
            total += pos.notional_value(last_price)
        return total

    def total_pnl(self, instrument_id: InstrumentId, last_price: Price) -> Decimal:
        return self.realized_pnl(instrument_id) + self.unrealized_pnl(instrument_id, last_price)

    def balance_total(self, venue: Venue, currency: Currency | None = None) -> Money | None:
        account = self._cache.account_for_venue(venue)
        if account is None:
            return None
        return account.balance_total(currency)

    def balance_free(self, venue: Venue, currency: Currency | None = None) -> Money | None:
        account = self._cache.account_for_venue(venue)
        if account is None:
            return None
        return account.balance_free(currency)

    def balance_locked(self, venue: Venue, currency: Currency | None = None) -> Money | None:
        account = self._cache.account_for_venue(venue)
        if account is None:
            return None
        return account.balance_locked(currency)
