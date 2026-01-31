from __future__ import annotations

from decimal import Decimal

from nautilus_core.cache import Cache
from nautilus_core.enums import TradingState
from nautilus_core.events import OrderDenied
from nautilus_core.identifiers import Venue
from nautilus_core.instruments import Instrument
from nautilus_core.msgbus import MessageBus
from nautilus_core.orders import Order
from nautilus_core.portfolio import Portfolio


class RiskEngine:
    def __init__(self, portfolio: Portfolio, cache: Cache, msgbus: MessageBus) -> None:
        self._portfolio = portfolio
        self._cache = cache
        self._msgbus = msgbus
        self.trading_state = TradingState.ACTIVE

    def set_trading_state(self, state: TradingState) -> None:
        self.trading_state = state

    def validate_order(self, order: Order) -> OrderDenied | None:
        if self.trading_state == TradingState.HALTED:
            return OrderDenied(
                trader_id=order.trader_id,
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason="Trading is HALTED",
            )

        instrument = self._cache.instrument(order.instrument_id)
        if instrument is None:
            return OrderDenied(
                trader_id=order.trader_id,
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=f"No instrument found for {order.instrument_id}",
            )

        # Validate quantity precision
        if order.quantity.precision != instrument.size_precision:
            return OrderDenied(
                trader_id=order.trader_id,
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=f"Invalid quantity precision {order.quantity.precision}, expected {instrument.size_precision}",
            )

        # Validate min/max quantity
        if instrument.min_quantity and order.quantity < instrument.min_quantity:
            return OrderDenied(
                trader_id=order.trader_id,
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=f"Quantity {order.quantity} below minimum {instrument.min_quantity}",
            )

        if instrument.max_quantity and order.quantity > instrument.max_quantity:
            return OrderDenied(
                trader_id=order.trader_id,
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=f"Quantity {order.quantity} above maximum {instrument.max_quantity}",
            )

        # Validate price for limit orders
        if hasattr(order, "price") and order.price is not None:
            if order.price <= 0:
                return OrderDenied(
                    trader_id=order.trader_id,
                    strategy_id=order.strategy_id,
                    instrument_id=order.instrument_id,
                    client_order_id=order.client_order_id,
                    reason="Price must be positive",
                )
            if order.price.precision != instrument.price_precision:
                return OrderDenied(
                    trader_id=order.trader_id,
                    strategy_id=order.strategy_id,
                    instrument_id=order.instrument_id,
                    client_order_id=order.client_order_id,
                    reason=f"Invalid price precision {order.price.precision}, expected {instrument.price_precision}",
                )

        # Check REDUCING state
        if self.trading_state == TradingState.REDUCING:
            from nautilus_core.enums import OrderSide
            net = self._portfolio.net_position(order.instrument_id)
            if (order.side == OrderSide.BUY and net >= 0) or (order.side == OrderSide.SELL and net <= 0):
                return OrderDenied(
                    trader_id=order.trader_id,
                    strategy_id=order.strategy_id,
                    instrument_id=order.instrument_id,
                    client_order_id=order.client_order_id,
                    reason="Trading state is REDUCING, only reducing orders allowed",
                )

        return None
