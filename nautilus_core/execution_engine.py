from __future__ import annotations

from typing import Any

from nautilus_core.cache import Cache
from nautilus_core.enums import OmsType, OrderSide, PositionSide
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
from nautilus_core.identifiers import PositionId, Venue
from nautilus_core.msgbus import MessageBus
from nautilus_core.orders import Order
from nautilus_core.position import Position
from nautilus_core.risk_engine import RiskEngine


class ExecutionEngine:
    def __init__(
        self,
        cache: Cache,
        msgbus: MessageBus,
        risk_engine: RiskEngine | None = None,
    ) -> None:
        self._cache = cache
        self._msgbus = msgbus
        self._risk_engine = risk_engine
        self._venues: dict[Venue, Any] = {}  # venue -> exchange/client
        self._oms_types: dict[Venue, OmsType] = {}
        self._position_counter = 0

    def register_venue(self, venue: Venue, exchange: Any, oms_type: OmsType = OmsType.HEDGING) -> None:
        self._venues[venue] = exchange
        self._oms_types[venue] = oms_type

    def submit_order(self, order: Order) -> None:
        # Risk check
        if self._risk_engine:
            denied = self._risk_engine.validate_order(order)
            if denied:
                order.apply(denied)
                self._cache.update_order(order)
                self._msgbus.publish(f"events.order.{order.strategy_id}", denied)
                return

        # Submit
        submitted = OrderSubmitted(
            trader_id=order.trader_id,
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            ts_event=order.ts_init,
            ts_init=order.ts_init,
        )
        order.apply(submitted)
        self._cache.add_order(order)
        self._msgbus.publish(f"events.order.{order.strategy_id}", submitted)

        # Route to venue
        venue = order.instrument_id.venue
        exchange = self._venues.get(venue)
        if exchange is not None:
            exchange.process_order(order)

    def cancel_order(self, order: Order) -> None:
        venue = order.instrument_id.venue
        exchange = self._venues.get(venue)
        if exchange is not None:
            exchange.cancel_order(order)

    def modify_order(self, order: Order, quantity=None, price=None, trigger_price=None) -> None:
        venue = order.instrument_id.venue
        exchange = self._venues.get(venue)
        if exchange is not None:
            exchange.modify_order(order, quantity=quantity, price=price, trigger_price=trigger_price)

    def process_event(self, event) -> None:
        """Process an order/position event from the exchange."""
        if isinstance(event, OrderFilled):
            self._handle_fill(event)
        elif isinstance(event, (OrderAccepted, OrderRejected, OrderCanceled)):
            self._handle_order_event(event)

    def _handle_order_event(self, event) -> None:
        order = self._cache.order(event.client_order_id)
        if order is None:
            return
        order.apply(event)
        self._cache.update_order(order)
        self._msgbus.publish(f"events.order.{order.strategy_id}", event)

    def _handle_fill(self, event: OrderFilled) -> None:
        order = self._cache.order(event.client_order_id)
        if order is None:
            return
        order.apply(event)
        self._cache.update_order(order)
        self._msgbus.publish(f"events.order.{order.strategy_id}", event)

        # Position management
        venue = order.instrument_id.venue
        oms_type = self._oms_types.get(venue, OmsType.HEDGING)

        if oms_type == OmsType.NETTING:
            self._handle_fill_netting(event, order)
        else:
            self._handle_fill_hedging(event, order)

    def _handle_fill_netting(self, event: OrderFilled, order: Order) -> None:
        instrument_id = order.instrument_id
        open_positions = self._cache.positions_open(instrument_id=instrument_id)

        if open_positions:
            position = open_positions[0]
            was_open = position.is_open
            position.apply(event)
            self._cache.update_position(position)

            if position.is_closed:
                pos_event = PositionClosed(
                    trader_id=event.trader_id,
                    strategy_id=event.strategy_id,
                    instrument_id=instrument_id,
                    position_id=position.id,
                    ts_event=event.ts_event,
                    ts_init=event.ts_init,
                )
                self._msgbus.publish(f"events.position.{order.strategy_id}", pos_event)
            else:
                pos_event = PositionChanged(
                    trader_id=event.trader_id,
                    strategy_id=event.strategy_id,
                    instrument_id=instrument_id,
                    position_id=position.id,
                    position_side=position.side,
                    signed_qty=position.signed_qty,
                    ts_event=event.ts_event,
                    ts_init=event.ts_init,
                )
                self._msgbus.publish(f"events.position.{order.strategy_id}", pos_event)
        else:
            self._open_position(event, order)

    def _handle_fill_hedging(self, event: OrderFilled, order: Order) -> None:
        if event.position_id:
            position = self._cache.position(event.position_id)
            if position:
                position.apply(event)
                self._cache.update_position(position)
                if position.is_closed:
                    pos_event = PositionClosed(
                        trader_id=event.trader_id,
                        strategy_id=event.strategy_id,
                        instrument_id=order.instrument_id,
                        position_id=position.id,
                        ts_event=event.ts_event,
                        ts_init=event.ts_init,
                    )
                    self._msgbus.publish(f"events.position.{order.strategy_id}", pos_event)
                else:
                    pos_event = PositionChanged(
                        trader_id=event.trader_id,
                        strategy_id=event.strategy_id,
                        instrument_id=order.instrument_id,
                        position_id=position.id,
                        position_side=position.side,
                        signed_qty=position.signed_qty,
                        ts_event=event.ts_event,
                        ts_init=event.ts_init,
                    )
                    self._msgbus.publish(f"events.position.{order.strategy_id}", pos_event)
                return

        # For netting-like behavior when no position_id specified, find matching open position
        open_positions = self._cache.positions_open(instrument_id=order.instrument_id)
        if open_positions:
            position = open_positions[0]
            position.apply(event)
            self._cache.update_position(position)
            if position.is_closed:
                pos_event = PositionClosed(
                    trader_id=event.trader_id,
                    strategy_id=event.strategy_id,
                    instrument_id=order.instrument_id,
                    position_id=position.id,
                    ts_event=event.ts_event,
                    ts_init=event.ts_init,
                )
                self._msgbus.publish(f"events.position.{order.strategy_id}", pos_event)
            else:
                pos_event = PositionChanged(
                    trader_id=event.trader_id,
                    strategy_id=event.strategy_id,
                    instrument_id=order.instrument_id,
                    position_id=position.id,
                    position_side=position.side,
                    signed_qty=position.signed_qty,
                    ts_event=event.ts_event,
                    ts_init=event.ts_init,
                )
                self._msgbus.publish(f"events.position.{order.strategy_id}", pos_event)
        else:
            self._open_position(event, order)

    def _open_position(self, event: OrderFilled, order: Order) -> None:
        self._position_counter += 1
        position_id = PositionId(f"P-{self._position_counter}")
        position = Position(order.instrument_id, position_id, event)
        self._cache.add_position(position)

        pos_event = PositionOpened(
            trader_id=event.trader_id,
            strategy_id=event.strategy_id,
            instrument_id=order.instrument_id,
            position_id=position_id,
            position_side=position.side,
            signed_qty=position.signed_qty,
            quantity=position.quantity,
            avg_px_open=position.avg_px_open,
            last_px=event.last_px,
            currency=event.currency,
            ts_event=event.ts_event,
            ts_init=event.ts_init,
        )
        self._msgbus.publish(f"events.position.{order.strategy_id}", pos_event)
