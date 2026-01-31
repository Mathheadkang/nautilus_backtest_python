from __future__ import annotations

from typing import TYPE_CHECKING

from nautilus_core.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_core.enums import OrderSide, OrderType, TimeInForce
from nautilus_core.events import (
    OrderAccepted,
    OrderCanceled,
    OrderDenied,
    OrderFilled,
    OrderRejected,
    OrderSubmitted,
    PositionChanged,
    PositionClosed,
    PositionOpened,
)
from nautilus_core.identifiers import InstrumentId, StrategyId
from nautilus_core.objects import Price, Quantity
from nautilus_core.orders import Order
from nautilus_core.trading.config import StrategyConfig

if TYPE_CHECKING:
    from nautilus_core.cache import Cache
    from nautilus_core.clock import Clock
    from nautilus_core.data_engine import DataEngine
    from nautilus_core.execution_engine import ExecutionEngine
    from nautilus_core.msgbus import MessageBus
    from nautilus_core.order_factory import OrderFactory
    from nautilus_core.portfolio import Portfolio


class Strategy:
    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig()
        self.id = StrategyId(self.config.strategy_id or type(self).__name__)

        # Injected by the engine
        self.clock: Clock | None = None
        self.cache: Cache | None = None
        self.portfolio: Portfolio | None = None
        self.msgbus: MessageBus | None = None
        self.order_factory: OrderFactory | None = None
        self._exec_engine: ExecutionEngine | None = None
        self._data_engine: DataEngine | None = None

        self._indicators: dict[BarType, list] = {}
        self._registered = False

    def register(
        self,
        clock: Clock,
        cache: Cache,
        portfolio: Portfolio,
        msgbus: MessageBus,
        order_factory: OrderFactory,
        exec_engine: ExecutionEngine,
        data_engine: DataEngine,
    ) -> None:
        self.clock = clock
        self.cache = cache
        self.portfolio = portfolio
        self.msgbus = msgbus
        self.order_factory = order_factory
        self._exec_engine = exec_engine
        self._data_engine = data_engine

        # Subscribe to order events
        msgbus.subscribe(f"events.order.{self.id}", self._handle_order_event)
        msgbus.subscribe(f"events.position.{self.id}", self._handle_position_event)

        self._registered = True

    # --- Lifecycle ---

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    def on_reset(self) -> None:
        pass

    # --- Data handlers ---

    def on_bar(self, bar: Bar) -> None:
        pass

    def on_quote_tick(self, tick: QuoteTick) -> None:
        pass

    def on_trade_tick(self, tick: TradeTick) -> None:
        pass

    def on_data(self, data) -> None:
        pass

    # --- Order event handlers ---

    def on_order_initialized(self, event) -> None:
        pass

    def on_order_submitted(self, event: OrderSubmitted) -> None:
        pass

    def on_order_accepted(self, event: OrderAccepted) -> None:
        pass

    def on_order_rejected(self, event: OrderRejected) -> None:
        pass

    def on_order_denied(self, event: OrderDenied) -> None:
        pass

    def on_order_filled(self, event: OrderFilled) -> None:
        pass

    def on_order_canceled(self, event: OrderCanceled) -> None:
        pass

    # --- Position event handlers ---

    def on_position_opened(self, event: PositionOpened) -> None:
        pass

    def on_position_changed(self, event: PositionChanged) -> None:
        pass

    def on_position_closed(self, event: PositionClosed) -> None:
        pass

    # --- Commands ---

    def submit_order(self, order: Order) -> None:
        if self._exec_engine:
            self._exec_engine.submit_order(order)

    def cancel_order(self, order: Order) -> None:
        if self._exec_engine:
            self._exec_engine.cancel_order(order)

    def modify_order(self, order: Order, quantity=None, price=None, trigger_price=None) -> None:
        if self._exec_engine:
            self._exec_engine.modify_order(order, quantity=quantity, price=price, trigger_price=trigger_price)

    def cancel_all_orders(self, instrument_id: InstrumentId) -> None:
        if self.cache:
            for order in self.cache.orders_open(instrument_id=instrument_id, strategy_id=self.id):
                self.cancel_order(order)

    def close_position(self, position, ts_init: int = 0) -> None:
        if position.is_open and self.order_factory:
            side = OrderSide.SELL if position.is_long else OrderSide.BUY
            order = self.order_factory.market(
                instrument_id=position.instrument_id,
                side=side,
                quantity=position.quantity,
                ts_init=ts_init,
            )
            self.submit_order(order)

    def close_all_positions(self, instrument_id: InstrumentId, ts_init: int = 0) -> None:
        if self.cache:
            for pos in self.cache.positions_open(instrument_id=instrument_id, strategy_id=self.id):
                self.close_position(pos, ts_init=ts_init)

    # --- Indicator registration ---

    def register_indicator_for_bars(self, bar_type: BarType, indicator) -> None:
        self._indicators.setdefault(bar_type, []).append(indicator)

    # --- Data subscriptions ---

    def subscribe_bars(self, bar_type: BarType) -> None:
        if self._data_engine:
            self._data_engine.subscribe_bars(bar_type)
        if self.msgbus:
            topic = f"data.bars.{bar_type}"
            self.msgbus.subscribe(topic, self._handle_bar)

    def subscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        if self._data_engine:
            self._data_engine.subscribe_quote_ticks(instrument_id)
        if self.msgbus:
            topic = f"data.quotes.{instrument_id}"
            self.msgbus.subscribe(topic, self._handle_quote_tick)

    def subscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        if self._data_engine:
            self._data_engine.subscribe_trade_ticks(instrument_id)
        if self.msgbus:
            topic = f"data.trades.{instrument_id}"
            self.msgbus.subscribe(topic, self._handle_trade_tick)

    # --- Internal handlers ---

    def _handle_bar(self, bar: Bar) -> None:
        # Feed indicators
        indicators = self._indicators.get(bar.bar_type, [])
        for indicator in indicators:
            indicator.handle_bar(bar)
        self.on_bar(bar)

    def _handle_quote_tick(self, tick: QuoteTick) -> None:
        self.on_quote_tick(tick)

    def _handle_trade_tick(self, tick: TradeTick) -> None:
        self.on_trade_tick(tick)

    def _handle_order_event(self, event) -> None:
        if isinstance(event, OrderSubmitted):
            self.on_order_submitted(event)
        elif isinstance(event, OrderAccepted):
            self.on_order_accepted(event)
        elif isinstance(event, OrderRejected):
            self.on_order_rejected(event)
        elif isinstance(event, OrderDenied):
            self.on_order_denied(event)
        elif isinstance(event, OrderFilled):
            self.on_order_filled(event)
        elif isinstance(event, OrderCanceled):
            self.on_order_canceled(event)

    def _handle_position_event(self, event) -> None:
        if isinstance(event, PositionOpened):
            self.on_position_opened(event)
        elif isinstance(event, PositionChanged):
            self.on_position_changed(event)
        elif isinstance(event, PositionClosed):
            self.on_position_closed(event)
