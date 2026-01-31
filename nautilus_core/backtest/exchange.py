from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from nautilus_core.account import Account, CashAccount, MarginAccount
from nautilus_core.enums import (
    AccountType,
    LiquiditySide,
    OmsType,
    OrderSide,
    OrderStatus,
    OrderType,
)
from nautilus_core.events import (
    OrderAccepted,
    OrderCanceled,
    OrderFilled,
    OrderRejected,
    OrderUpdated,
)
from nautilus_core.identifiers import AccountId, TradeId, Venue, VenueOrderId
from nautilus_core.objects import Currency, Money, Price, Quantity

if TYPE_CHECKING:
    from nautilus_core.data import Bar
    from nautilus_core.execution_engine import ExecutionEngine
    from nautilus_core.instruments import Instrument
    from nautilus_core.orders import LimitOrder, Order, StopLimitOrder, StopMarketOrder


class SimulatedExchange:
    def __init__(
        self,
        venue: Venue,
        oms_type: OmsType,
        account_type: AccountType,
        base_currency: Currency,
        starting_balances: list[Money],
        exec_engine: ExecutionEngine | None = None,
        default_leverage: Decimal = Decimal("1"),
        fill_model: str = "mid",  # "mid", "worst"
    ) -> None:
        self.venue = venue
        self.oms_type = oms_type
        self.account_type = account_type
        self.base_currency = base_currency
        self.fill_model = fill_model

        # Create account
        account_id = AccountId(f"{venue.value}-001")
        if account_type == AccountType.MARGIN:
            self.account = MarginAccount(account_id, base_currency, leverage=default_leverage)
        else:
            self.account = CashAccount(account_id, base_currency)

        # Set starting balances
        for money in starting_balances:
            self.account.update_balance(money.currency, money.amount, Decimal("0"))

        self._exec_engine: ExecutionEngine | None = exec_engine
        self._instruments: dict = {}
        self._open_orders: list[Order] = []
        self._venue_order_counter = 0
        self._trade_counter = 0

    def set_exec_engine(self, exec_engine: ExecutionEngine) -> None:
        self._exec_engine = exec_engine

    def add_instrument(self, instrument: Instrument) -> None:
        self._instruments[instrument.id] = instrument

    def process_order(self, order: Order) -> None:
        """Process incoming order — accept and potentially fill immediately."""
        self._venue_order_counter += 1
        venue_order_id = VenueOrderId(f"V-{self.venue.value}-{self._venue_order_counter}")

        # Accept order
        accepted = OrderAccepted(
            trader_id=order.trader_id,
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            venue_order_id=venue_order_id,
            account_id=self.account.id,
            ts_event=order.ts_init,
            ts_init=order.ts_init,
        )
        if self._exec_engine:
            self._exec_engine.process_event(accepted)

        # Market orders fill immediately at current price (we defer to bar processing)
        if order.order_type == OrderType.MARKET:
            # We'll fill at the next bar's open, but if we have no bar yet,
            # queue it. The backtest engine will call process_bar which handles this.
            self._open_orders.append(order)
        elif order.order_type in (OrderType.LIMIT, OrderType.STOP_MARKET, OrderType.STOP_LIMIT):
            self._open_orders.append(order)

    def cancel_order(self, order: Order) -> None:
        if order in self._open_orders:
            self._open_orders.remove(order)
            canceled = OrderCanceled(
                trader_id=order.trader_id,
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                venue_order_id=order.venue_order_id,
                account_id=self.account.id,
                ts_event=order.ts_last,
                ts_init=order.ts_last,
            )
            if self._exec_engine:
                self._exec_engine.process_event(canceled)

    def modify_order(self, order: Order, quantity=None, price=None, trigger_price=None) -> None:
        updated = OrderUpdated(
            trader_id=order.trader_id,
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            venue_order_id=order.venue_order_id,
            account_id=self.account.id,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            ts_event=order.ts_last,
            ts_init=order.ts_last,
        )
        if self._exec_engine:
            self._exec_engine.process_event(updated)

    def process_bar(self, bar: Bar) -> None:
        """Process bar through matching engine — check fills for open orders."""
        orders_to_remove = []
        for order in self._open_orders:
            if order.instrument_id != bar.bar_type.instrument_id:
                continue
            if not order.is_open:
                orders_to_remove.append(order)
                continue

            fill_px = self._check_fill(order, bar)
            if fill_px is not None:
                self._fill_order(order, fill_px, bar.ts_event)
                orders_to_remove.append(order)

        for order in orders_to_remove:
            if order in self._open_orders:
                self._open_orders.remove(order)

    def _check_fill(self, order: Order, bar: Bar) -> Price | None:
        """Check if order should fill given the bar's OHLCV."""
        instrument = self._instruments.get(order.instrument_id)
        price_prec = instrument.price_precision if instrument else bar.open.precision

        if order.order_type == OrderType.MARKET:
            # Fill at bar open
            return bar.open

        elif order.order_type == OrderType.LIMIT:
            limit_px = order.price
            if order.side == OrderSide.BUY:
                # Buy limit fills if price goes at or below limit
                if bar.low <= limit_px:
                    return Price(min(limit_px.value, bar.open.value), price_prec)
            else:
                # Sell limit fills if price goes at or above limit
                if bar.high >= limit_px:
                    return Price(max(limit_px.value, bar.open.value), price_prec)

        elif order.order_type == OrderType.STOP_MARKET:
            trigger_px = order.trigger_price
            if order.side == OrderSide.BUY:
                # Buy stop triggers if price goes at or above trigger
                if bar.high >= trigger_px:
                    return Price(max(trigger_px.value, bar.open.value), price_prec)
            else:
                # Sell stop triggers if price goes at or below trigger
                if bar.low <= trigger_px:
                    return Price(min(trigger_px.value, bar.open.value), price_prec)

        elif order.order_type == OrderType.STOP_LIMIT:
            trigger_px = order.trigger_price
            limit_px = order.price
            if order.side == OrderSide.BUY:
                if bar.high >= trigger_px:
                    if bar.low <= limit_px:
                        return Price(min(limit_px.value, max(trigger_px.value, bar.open.value)), price_prec)
            else:
                if bar.low <= trigger_px:
                    if bar.high >= limit_px:
                        return Price(max(limit_px.value, min(trigger_px.value, bar.open.value)), price_prec)

        return None

    def _fill_order(self, order: Order, fill_px: Price, ts_event: int) -> None:
        instrument = self._instruments.get(order.instrument_id)
        commission_rate = Decimal("0")
        if instrument:
            commission_rate = instrument.taker_fee

        fill_qty = order.leaves_qty
        notional = fill_qty.value * fill_px.value
        commission_amount = notional * commission_rate
        commission = Money(commission_amount, self.base_currency)

        self._trade_counter += 1
        trade_id = TradeId(f"T-{self.venue.value}-{self._trade_counter}")

        filled = OrderFilled(
            trader_id=order.trader_id,
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            venue_order_id=order.venue_order_id,
            account_id=self.account.id,
            trade_id=trade_id,
            order_side=order.side,
            order_type=order.order_type,
            last_qty=fill_qty,
            last_px=fill_px,
            currency=self.base_currency,
            commission=commission,
            liquidity_side=LiquiditySide.TAKER,
            ts_event=ts_event,
            ts_init=ts_event,
        )

        # Update account balance
        if order.side == OrderSide.BUY:
            cost = notional + commission_amount
            current = self.account.balance_free(self.base_currency)
            if current:
                new_total = current.amount - cost
                self.account.update_balance(self.base_currency, new_total, Decimal("0"))
        else:
            revenue = notional - commission_amount
            current = self.account.balance_free(self.base_currency)
            if current:
                new_total = current.amount + revenue
                self.account.update_balance(self.base_currency, new_total, Decimal("0"))

        self.account.update_commissions(self.base_currency, commission_amount)

        if self._exec_engine:
            self._exec_engine.process_event(filled)

    @property
    def open_order_count(self) -> int:
        return len(self._open_orders)
