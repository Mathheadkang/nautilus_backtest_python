from __future__ import annotations

from nautilus_core.enums import OrderSide, OrderType, TimeInForce
from nautilus_core.events import OrderInitialized
from nautilus_core.identifiers import ClientOrderId, InstrumentId, StrategyId, TraderId
from nautilus_core.objects import Price, Quantity
from nautilus_core.orders import LimitOrder, MarketOrder, Order, StopLimitOrder, StopMarketOrder


class OrderFactory:
    def __init__(self, trader_id: TraderId, strategy_id: StrategyId) -> None:
        self.trader_id = trader_id
        self.strategy_id = strategy_id
        self._counter = 0

    def _next_order_id(self) -> ClientOrderId:
        self._counter += 1
        return ClientOrderId(f"O-{self.strategy_id.value}-{self._counter}")

    def reset(self) -> None:
        self._counter = 0

    def market(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        time_in_force: TimeInForce = TimeInForce.GTC,
        ts_init: int = 0,
    ) -> MarketOrder:
        init = OrderInitialized(
            trader_id=self.trader_id,
            strategy_id=self.strategy_id,
            instrument_id=instrument_id,
            client_order_id=self._next_order_id(),
            order_side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            time_in_force=time_in_force,
            ts_init=ts_init,
        )
        return MarketOrder(init)

    def limit(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        price: Price,
        time_in_force: TimeInForce = TimeInForce.GTC,
        ts_init: int = 0,
    ) -> LimitOrder:
        init = OrderInitialized(
            trader_id=self.trader_id,
            strategy_id=self.strategy_id,
            instrument_id=instrument_id,
            client_order_id=self._next_order_id(),
            order_side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            time_in_force=time_in_force,
            price=price,
            ts_init=ts_init,
        )
        return LimitOrder(init)

    def stop_market(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        trigger_price: Price,
        time_in_force: TimeInForce = TimeInForce.GTC,
        ts_init: int = 0,
    ) -> StopMarketOrder:
        init = OrderInitialized(
            trader_id=self.trader_id,
            strategy_id=self.strategy_id,
            instrument_id=instrument_id,
            client_order_id=self._next_order_id(),
            order_side=side,
            order_type=OrderType.STOP_MARKET,
            quantity=quantity,
            time_in_force=time_in_force,
            trigger_price=trigger_price,
            ts_init=ts_init,
        )
        return StopMarketOrder(init)

    def stop_limit(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        quantity: Quantity,
        price: Price,
        trigger_price: Price,
        time_in_force: TimeInForce = TimeInForce.GTC,
        ts_init: int = 0,
    ) -> StopLimitOrder:
        init = OrderInitialized(
            trader_id=self.trader_id,
            strategy_id=self.strategy_id,
            instrument_id=instrument_id,
            client_order_id=self._next_order_id(),
            order_side=side,
            order_type=OrderType.STOP_LIMIT,
            quantity=quantity,
            time_in_force=time_in_force,
            price=price,
            trigger_price=trigger_price,
            ts_init=ts_init,
        )
        return StopLimitOrder(init)
