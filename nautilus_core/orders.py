from __future__ import annotations

from decimal import Decimal

from nautilus_core.enums import (
    ORDER_STATUS_TRANSITIONS,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from nautilus_core.events import (
    OrderAccepted,
    OrderCanceled,
    OrderDenied,
    OrderExpired,
    OrderFilled,
    OrderInitialized,
    OrderRejected,
    OrderSubmitted,
    OrderUpdated,
)
from nautilus_core.identifiers import (
    ClientOrderId,
    InstrumentId,
    StrategyId,
    TraderId,
    VenueOrderId,
)
from nautilus_core.objects import Price, Quantity

_EVENT_TO_STATUS = {
    OrderInitialized: OrderStatus.INITIALIZED,
    OrderDenied: OrderStatus.DENIED,
    OrderSubmitted: OrderStatus.SUBMITTED,
    OrderAccepted: OrderStatus.ACCEPTED,
    OrderRejected: OrderStatus.REJECTED,
    OrderCanceled: OrderStatus.CANCELED,
    OrderExpired: OrderStatus.EXPIRED,
    OrderUpdated: None,  # handled specially
    OrderFilled: None,   # handled specially
}


class Order:
    def __init__(
        self,
        init: OrderInitialized,
    ) -> None:
        self.client_order_id = init.client_order_id
        self.instrument_id = init.instrument_id
        self.trader_id = init.trader_id
        self.strategy_id = init.strategy_id
        self.side = init.order_side
        self.order_type = init.order_type
        self.quantity = init.quantity
        self.time_in_force = init.time_in_force
        self.status = OrderStatus.INITIALIZED
        self.filled_qty = Quantity(0, init.quantity.precision)
        self.leaves_qty = Quantity(init.quantity.value, init.quantity.precision)
        self.avg_px: Decimal = Decimal("0")
        self.venue_order_id: VenueOrderId | None = None
        self.events: list = [init]
        self.ts_init = init.ts_init
        self.ts_last = init.ts_event

    @property
    def is_open(self) -> bool:
        return self.status in {
            OrderStatus.ACCEPTED,
            OrderStatus.TRIGGERED,
            OrderStatus.PENDING_UPDATE,
            OrderStatus.PENDING_CANCEL,
            OrderStatus.PARTIALLY_FILLED,
        }

    @property
    def is_closed(self) -> bool:
        return self.status in {
            OrderStatus.DENIED,
            OrderStatus.REJECTED,
            OrderStatus.CANCELED,
            OrderStatus.EXPIRED,
            OrderStatus.FILLED,
        }

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    def apply(self, event) -> None:
        if isinstance(event, OrderFilled):
            self._apply_filled(event)
        elif isinstance(event, OrderUpdated):
            self._apply_updated(event)
        else:
            new_status = _EVENT_TO_STATUS.get(type(event))
            if new_status is None:
                raise ValueError(f"Unknown order event type: {type(event).__name__}")
            self._check_transition(new_status)
            self.status = new_status
            if isinstance(event, OrderAccepted) and event.venue_order_id:
                self.venue_order_id = event.venue_order_id
        self.events.append(event)
        self.ts_last = event.ts_event

    def _apply_filled(self, event: OrderFilled) -> None:
        fill_qty = event.last_qty.value
        fill_px = event.last_px.value
        prev_filled = self.filled_qty.value
        new_filled = prev_filled + fill_qty

        # Weighted average price
        if new_filled > 0:
            self.avg_px = (self.avg_px * prev_filled + fill_px * fill_qty) / new_filled

        self.filled_qty = Quantity(new_filled, self.quantity.precision)
        self.leaves_qty = Quantity(self.quantity.value - new_filled, self.quantity.precision)

        if self.leaves_qty.value == 0:
            new_status = OrderStatus.FILLED
        else:
            new_status = OrderStatus.PARTIALLY_FILLED

        self._check_transition(new_status)
        self.status = new_status

        if event.venue_order_id:
            self.venue_order_id = event.venue_order_id

    def _apply_updated(self, event: OrderUpdated) -> None:
        if event.quantity is not None:
            self.quantity = event.quantity
            self.leaves_qty = Quantity(
                event.quantity.value - self.filled_qty.value,
                event.quantity.precision,
            )
        new_status = OrderStatus.ACCEPTED
        self._check_transition(new_status)
        self.status = new_status

    def _check_transition(self, new_status: OrderStatus) -> None:
        valid = ORDER_STATUS_TRANSITIONS.get(self.status, set())
        if new_status not in valid:
            raise RuntimeError(
                f"Invalid order state transition: {self.status.name} -> {new_status.name}"
            )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"id={self.client_order_id}, "
            f"{self.side.name} {self.quantity} {self.instrument_id}, "
            f"status={self.status.name})"
        )


class MarketOrder(Order):
    def __init__(self, init: OrderInitialized) -> None:
        if init.order_type != OrderType.MARKET:
            raise ValueError(f"Expected MARKET order type, got {init.order_type}")
        super().__init__(init)


class LimitOrder(Order):
    def __init__(self, init: OrderInitialized) -> None:
        if init.order_type != OrderType.LIMIT:
            raise ValueError(f"Expected LIMIT order type, got {init.order_type}")
        if init.price is None:
            raise ValueError("LimitOrder requires a price")
        super().__init__(init)
        self.price = init.price

    def _apply_updated(self, event: OrderUpdated) -> None:
        super()._apply_updated(event)
        if event.price is not None:
            self.price = event.price


class StopMarketOrder(Order):
    def __init__(self, init: OrderInitialized) -> None:
        if init.order_type != OrderType.STOP_MARKET:
            raise ValueError(f"Expected STOP_MARKET order type, got {init.order_type}")
        if init.trigger_price is None:
            raise ValueError("StopMarketOrder requires a trigger_price")
        super().__init__(init)
        self.trigger_price = init.trigger_price

    def _apply_updated(self, event: OrderUpdated) -> None:
        super()._apply_updated(event)
        if event.trigger_price is not None:
            self.trigger_price = event.trigger_price


class StopLimitOrder(Order):
    def __init__(self, init: OrderInitialized) -> None:
        if init.order_type != OrderType.STOP_LIMIT:
            raise ValueError(f"Expected STOP_LIMIT order type, got {init.order_type}")
        if init.trigger_price is None:
            raise ValueError("StopLimitOrder requires a trigger_price")
        if init.price is None:
            raise ValueError("StopLimitOrder requires a price")
        super().__init__(init)
        self.trigger_price = init.trigger_price
        self.price = init.price

    def _apply_updated(self, event: OrderUpdated) -> None:
        super()._apply_updated(event)
        if event.price is not None:
            self.price = event.price
        if event.trigger_price is not None:
            self.trigger_price = event.trigger_price
