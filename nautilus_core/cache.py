from __future__ import annotations

from nautilus_core.account import Account
from nautilus_core.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_core.enums import OrderStatus
from nautilus_core.identifiers import (
    AccountId,
    ClientOrderId,
    InstrumentId,
    PositionId,
    StrategyId,
    Venue,
)
from nautilus_core.instruments import Instrument
from nautilus_core.orders import Order
from nautilus_core.position import Position


class Cache:
    def __init__(self) -> None:
        self._instruments: dict[InstrumentId, Instrument] = {}
        self._accounts: dict[AccountId, Account] = {}
        self._orders: dict[ClientOrderId, Order] = {}
        self._positions: dict[PositionId, Position] = {}
        self._bars: dict[BarType, list[Bar]] = {}
        self._quote_ticks: dict[InstrumentId, list[QuoteTick]] = {}
        self._trade_ticks: dict[InstrumentId, list[TradeTick]] = {}
        # Index maps
        self._orders_by_venue: dict[Venue, list[ClientOrderId]] = {}
        self._orders_by_strategy: dict[StrategyId, list[ClientOrderId]] = {}
        self._orders_by_instrument: dict[InstrumentId, list[ClientOrderId]] = {}
        self._positions_by_venue: dict[Venue, list[PositionId]] = {}
        self._positions_by_strategy: dict[StrategyId, list[PositionId]] = {}
        self._positions_by_instrument: dict[InstrumentId, list[PositionId]] = {}

    # --- Instruments ---

    def add_instrument(self, instrument: Instrument) -> None:
        self._instruments[instrument.id] = instrument

    def instrument(self, instrument_id: InstrumentId) -> Instrument | None:
        return self._instruments.get(instrument_id)

    def instruments(self) -> list[Instrument]:
        return list(self._instruments.values())

    # --- Accounts ---

    def add_account(self, account: Account) -> None:
        self._accounts[account.id] = account

    def account(self, account_id: AccountId) -> Account | None:
        return self._accounts.get(account_id)

    def account_for_venue(self, venue: Venue) -> Account | None:
        for aid, acc in self._accounts.items():
            if venue.value in aid.value:
                return acc
        return None

    def accounts(self) -> list[Account]:
        return list(self._accounts.values())

    # --- Orders ---

    def add_order(self, order: Order) -> None:
        oid = order.client_order_id
        self._orders[oid] = order
        venue = order.instrument_id.venue
        self._orders_by_venue.setdefault(venue, []).append(oid)
        if order.strategy_id:
            self._orders_by_strategy.setdefault(order.strategy_id, []).append(oid)
        self._orders_by_instrument.setdefault(order.instrument_id, []).append(oid)

    def update_order(self, order: Order) -> None:
        self._orders[order.client_order_id] = order

    def order(self, client_order_id: ClientOrderId) -> Order | None:
        return self._orders.get(client_order_id)

    def orders(self, instrument_id: InstrumentId | None = None, strategy_id: StrategyId | None = None) -> list[Order]:
        if instrument_id:
            ids = self._orders_by_instrument.get(instrument_id, [])
            return [self._orders[oid] for oid in ids if oid in self._orders]
        if strategy_id:
            ids = self._orders_by_strategy.get(strategy_id, [])
            return [self._orders[oid] for oid in ids if oid in self._orders]
        return list(self._orders.values())

    def orders_open(self, instrument_id: InstrumentId | None = None, strategy_id: StrategyId | None = None) -> list[Order]:
        return [o for o in self.orders(instrument_id, strategy_id) if o.is_open]

    def orders_closed(self, instrument_id: InstrumentId | None = None, strategy_id: StrategyId | None = None) -> list[Order]:
        return [o for o in self.orders(instrument_id, strategy_id) if o.is_closed]

    def orders_for_venue(self, venue: Venue) -> list[Order]:
        ids = self._orders_by_venue.get(venue, [])
        return [self._orders[oid] for oid in ids if oid in self._orders]

    # --- Positions ---

    def add_position(self, position: Position) -> None:
        pid = position.id
        self._positions[pid] = position
        venue = position.instrument_id.venue
        self._positions_by_venue.setdefault(venue, []).append(pid)
        if position.strategy_id:
            self._positions_by_strategy.setdefault(position.strategy_id, []).append(pid)
        self._positions_by_instrument.setdefault(position.instrument_id, []).append(pid)

    def update_position(self, position: Position) -> None:
        self._positions[position.id] = position

    def position(self, position_id: PositionId) -> Position | None:
        return self._positions.get(position_id)

    def positions(self, instrument_id: InstrumentId | None = None, strategy_id: StrategyId | None = None) -> list[Position]:
        if instrument_id:
            ids = self._positions_by_instrument.get(instrument_id, [])
            return [self._positions[pid] for pid in ids if pid in self._positions]
        if strategy_id:
            ids = self._positions_by_strategy.get(strategy_id, [])
            return [self._positions[pid] for pid in ids if pid in self._positions]
        return list(self._positions.values())

    def positions_open(self, instrument_id: InstrumentId | None = None, strategy_id: StrategyId | None = None) -> list[Position]:
        return [p for p in self.positions(instrument_id, strategy_id) if p.is_open]

    def positions_closed(self, instrument_id: InstrumentId | None = None, strategy_id: StrategyId | None = None) -> list[Position]:
        return [p for p in self.positions(instrument_id, strategy_id) if p.is_closed]

    def positions_for_venue(self, venue: Venue) -> list[Position]:
        ids = self._positions_by_venue.get(venue, [])
        return [self._positions[pid] for pid in ids if pid in self._positions]

    # --- Bars ---

    def add_bar(self, bar: Bar) -> None:
        self._bars.setdefault(bar.bar_type, []).append(bar)

    def bars(self, bar_type: BarType) -> list[Bar]:
        return list(self._bars.get(bar_type, []))

    # --- Ticks ---

    def add_quote_tick(self, tick: QuoteTick) -> None:
        self._quote_ticks.setdefault(tick.instrument_id, []).append(tick)

    def quote_ticks(self, instrument_id: InstrumentId) -> list[QuoteTick]:
        return list(self._quote_ticks.get(instrument_id, []))

    def add_trade_tick(self, tick: TradeTick) -> None:
        self._trade_ticks.setdefault(tick.instrument_id, []).append(tick)

    def trade_ticks(self, instrument_id: InstrumentId) -> list[TradeTick]:
        return list(self._trade_ticks.get(instrument_id, []))
