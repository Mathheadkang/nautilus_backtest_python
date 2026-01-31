from __future__ import annotations

from decimal import Decimal

from nautilus_core.enums import OrderSide, PositionSide
from nautilus_core.events import OrderFilled
from nautilus_core.identifiers import InstrumentId, PositionId, StrategyId, TraderId
from nautilus_core.objects import Currency, Money, Price, Quantity


class Position:
    def __init__(self, instrument_id: InstrumentId, position_id: PositionId, fill: OrderFilled) -> None:
        self.instrument_id = instrument_id
        self.id = position_id
        self.trader_id = fill.trader_id
        self.strategy_id = fill.strategy_id
        self.account_id = fill.account_id
        self.currency = fill.currency

        self.side = PositionSide.FLAT
        self.quantity = Quantity(0, fill.last_qty.precision)
        self.signed_qty = Decimal("0")
        self.avg_px_open = Decimal("0")
        self.avg_px_close = Decimal("0")
        self.realized_pnl = Decimal("0")
        self.commissions: dict[Currency, Decimal] = {}
        self._events: list[OrderFilled] = []
        self._qty_precision = fill.last_qty.precision
        self._px_precision = fill.last_px.precision

        self.apply(fill)

    @property
    def is_open(self) -> bool:
        return self.side != PositionSide.FLAT

    @property
    def is_closed(self) -> bool:
        return self.side == PositionSide.FLAT and len(self._events) > 0

    @property
    def is_long(self) -> bool:
        return self.side == PositionSide.LONG

    @property
    def is_short(self) -> bool:
        return self.side == PositionSide.SHORT

    @property
    def events(self) -> list[OrderFilled]:
        return list(self._events)

    @property
    def ts_opened(self) -> int:
        return self._events[0].ts_event if self._events else 0

    @property
    def ts_closed(self) -> int | None:
        if self.is_closed:
            return self._events[-1].ts_event
        return None

    def apply(self, fill: OrderFilled) -> None:
        fill_qty = fill.last_qty.value
        fill_px = fill.last_px.value

        # Track commission
        if fill.commission:
            curr = fill.commission.currency
            self.commissions[curr] = self.commissions.get(curr, Decimal("0")) + fill.commission.amount

        if fill.order_side == OrderSide.BUY:
            self._apply_buy(fill_qty, fill_px)
        else:
            self._apply_sell(fill_qty, fill_px)

        self._events.append(fill)

    def _apply_buy(self, fill_qty: Decimal, fill_px: Decimal) -> None:
        if self.side == PositionSide.FLAT or self.side == PositionSide.LONG:
            # Opening or adding to long
            total_qty = abs(self.signed_qty) + fill_qty
            if total_qty > 0:
                self.avg_px_open = (self.avg_px_open * abs(self.signed_qty) + fill_px * fill_qty) / total_qty
            self.signed_qty += fill_qty
        elif self.side == PositionSide.SHORT:
            # Closing or reducing short
            close_qty = min(fill_qty, abs(self.signed_qty))
            pnl = close_qty * (self.avg_px_open - fill_px)
            self.realized_pnl += pnl

            remaining = fill_qty - close_qty
            self.signed_qty += fill_qty

            if remaining > 0:
                # Flipped to long
                self.avg_px_open = fill_px
                self.avg_px_close = fill_px
            elif self.signed_qty == 0:
                self.avg_px_close = fill_px

        self._update_side_and_qty()

    def _apply_sell(self, fill_qty: Decimal, fill_px: Decimal) -> None:
        if self.side == PositionSide.FLAT or self.side == PositionSide.SHORT:
            # Opening or adding to short
            total_qty = abs(self.signed_qty) + fill_qty
            if total_qty > 0:
                self.avg_px_open = (self.avg_px_open * abs(self.signed_qty) + fill_px * fill_qty) / total_qty
            self.signed_qty -= fill_qty
        elif self.side == PositionSide.LONG:
            # Closing or reducing long
            close_qty = min(fill_qty, abs(self.signed_qty))
            pnl = close_qty * (fill_px - self.avg_px_open)
            self.realized_pnl += pnl

            remaining = fill_qty - close_qty
            self.signed_qty -= fill_qty

            if remaining > 0:
                # Flipped to short
                self.avg_px_open = fill_px
                self.avg_px_close = fill_px
            elif self.signed_qty == 0:
                self.avg_px_close = fill_px

        self._update_side_and_qty()

    def _update_side_and_qty(self) -> None:
        if self.signed_qty > 0:
            self.side = PositionSide.LONG
        elif self.signed_qty < 0:
            self.side = PositionSide.SHORT
        else:
            self.side = PositionSide.FLAT
        self.quantity = Quantity(abs(self.signed_qty), self._qty_precision)

    def unrealized_pnl(self, last_price: Price) -> Decimal:
        if self.side == PositionSide.FLAT:
            return Decimal("0")
        last_px = last_price.value
        if self.side == PositionSide.LONG:
            return abs(self.signed_qty) * (last_px - self.avg_px_open)
        else:
            return abs(self.signed_qty) * (self.avg_px_open - last_px)

    def total_pnl(self, last_price: Price) -> Decimal:
        return self.realized_pnl + self.unrealized_pnl(last_price)

    def notional_value(self, last_price: Price) -> Decimal:
        return abs(self.signed_qty) * last_price.value

    def total_commissions(self) -> dict[Currency, Decimal]:
        return dict(self.commissions)

    def __repr__(self) -> str:
        return (
            f"Position(id={self.id}, {self.instrument_id}, "
            f"{self.side.name}, qty={self.quantity}, "
            f"avg_open={self.avg_px_open})"
        )
