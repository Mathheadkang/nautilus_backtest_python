from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from nautilus_core.enums import (
    AccountType,
    LiquiditySide,
    OrderSide,
    OrderType,
    PositionSide,
    TimeInForce,
)
from nautilus_core.identifiers import (
    AccountId,
    ClientOrderId,
    InstrumentId,
    PositionId,
    StrategyId,
    TradeId,
    TraderId,
    VenueOrderId,
)
from nautilus_core.objects import AccountBalance, Currency, Money, Price, Quantity


def _uuid() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class Event:
    event_id: str = field(default_factory=_uuid)
    ts_event: int = 0
    ts_init: int = 0


# --- Order events ---

@dataclass(frozen=True)
class OrderInitialized(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    order_side: OrderSide | None = None
    order_type: OrderType | None = None
    quantity: Quantity | None = None
    time_in_force: TimeInForce = TimeInForce.GTC
    price: Price | None = None
    trigger_price: Price | None = None


@dataclass(frozen=True)
class OrderDenied(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    reason: str = ""


@dataclass(frozen=True)
class OrderSubmitted(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    account_id: AccountId | None = None


@dataclass(frozen=True)
class OrderAccepted(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    venue_order_id: VenueOrderId | None = None
    account_id: AccountId | None = None


@dataclass(frozen=True)
class OrderRejected(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    reason: str = ""


@dataclass(frozen=True)
class OrderCanceled(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    venue_order_id: VenueOrderId | None = None
    account_id: AccountId | None = None


@dataclass(frozen=True)
class OrderExpired(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    venue_order_id: VenueOrderId | None = None
    account_id: AccountId | None = None


@dataclass(frozen=True)
class OrderUpdated(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    venue_order_id: VenueOrderId | None = None
    account_id: AccountId | None = None
    quantity: Quantity | None = None
    price: Price | None = None
    trigger_price: Price | None = None


@dataclass(frozen=True)
class OrderFilled(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    client_order_id: ClientOrderId | None = None
    venue_order_id: VenueOrderId | None = None
    account_id: AccountId | None = None
    trade_id: TradeId | None = None
    position_id: PositionId | None = None
    order_side: OrderSide | None = None
    order_type: OrderType | None = None
    last_qty: Quantity | None = None
    last_px: Price | None = None
    currency: Currency | None = None
    commission: Money | None = None
    liquidity_side: LiquiditySide = LiquiditySide.TAKER


# --- Position events ---

@dataclass(frozen=True)
class PositionOpened(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    position_id: PositionId | None = None
    position_side: PositionSide | None = None
    signed_qty: Decimal = Decimal("0")
    quantity: Quantity | None = None
    avg_px_open: Decimal = Decimal("0")
    last_px: Price | None = None
    currency: Currency | None = None


@dataclass(frozen=True)
class PositionChanged(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    position_id: PositionId | None = None
    position_side: PositionSide | None = None
    signed_qty: Decimal = Decimal("0")
    quantity: Quantity | None = None
    avg_px_open: Decimal = Decimal("0")
    avg_px_close: Decimal = Decimal("0")
    realized_pnl: Money | None = None
    unrealized_pnl: Money | None = None
    last_px: Price | None = None
    currency: Currency | None = None


@dataclass(frozen=True)
class PositionClosed(Event):
    trader_id: TraderId | None = None
    strategy_id: StrategyId | None = None
    instrument_id: InstrumentId | None = None
    position_id: PositionId | None = None
    signed_qty: Decimal = Decimal("0")
    quantity: Quantity | None = None
    avg_px_open: Decimal = Decimal("0")
    avg_px_close: Decimal = Decimal("0")
    realized_pnl: Money | None = None
    last_px: Price | None = None
    currency: Currency | None = None


# --- Account events ---

@dataclass(frozen=True)
class AccountState(Event):
    account_id: AccountId | None = None
    account_type: AccountType | None = None
    base_currency: Currency | None = None
    balances: list[AccountBalance] = field(default_factory=list)
    is_reported: bool = False
