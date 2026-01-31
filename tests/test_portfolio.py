from decimal import Decimal

import pytest

from nautilus_core.account import CashAccount
from nautilus_core.cache import Cache
from nautilus_core.enums import OrderSide, OrderType, PositionSide
from nautilus_core.events import OrderFilled
from nautilus_core.identifiers import (
    AccountId,
    ClientOrderId,
    InstrumentId,
    PositionId,
    StrategyId,
    Symbol,
    TradeId,
    TraderId,
    Venue,
    VenueOrderId,
)
from nautilus_core.objects import USD, AccountBalance, Money, Price, Quantity
from nautilus_core.portfolio import Portfolio
from nautilus_core.position import Position


def _instrument_id():
    return InstrumentId(Symbol("AAPL"), Venue("SIM"))


def _make_fill(side, qty, px):
    return OrderFilled(
        trader_id=TraderId("TESTER-001"),
        strategy_id=StrategyId("S-001"),
        instrument_id=_instrument_id(),
        client_order_id=ClientOrderId("O-001"),
        venue_order_id=VenueOrderId("V-001"),
        account_id=AccountId("SIM-001"),
        trade_id=TradeId("T-001"),
        order_side=side,
        order_type=OrderType.MARKET,
        last_qty=Quantity(qty, 0),
        last_px=Price(px, 2),
        currency=USD,
        commission=Money("0.00", USD),
    )


class TestPortfolio:
    def setup_method(self):
        self.cache = Cache()
        self.portfolio = Portfolio(self.cache)
        # Add account
        account = CashAccount(
            AccountId("SIM-001"),
            USD,
            [AccountBalance(Money("100000.00", USD), Money("0.00", USD), Money("100000.00", USD))],
        )
        self.cache.add_account(account)

    def test_flat_when_no_positions(self):
        assert self.portfolio.is_flat(_instrument_id())
        assert self.portfolio.net_position(_instrument_id()) == Decimal("0")

    def test_net_long(self):
        fill = _make_fill(OrderSide.BUY, "100", "150.00")
        pos = Position(_instrument_id(), PositionId("P-001"), fill)
        self.cache.add_position(pos)

        assert self.portfolio.is_net_long(_instrument_id())
        assert not self.portfolio.is_net_short(_instrument_id())
        assert self.portfolio.net_position(_instrument_id()) == Decimal("100")

    def test_net_short(self):
        fill = _make_fill(OrderSide.SELL, "100", "150.00")
        pos = Position(_instrument_id(), PositionId("P-001"), fill)
        self.cache.add_position(pos)

        assert self.portfolio.is_net_short(_instrument_id())
        assert not self.portfolio.is_net_long(_instrument_id())

    def test_unrealized_pnl(self):
        fill = _make_fill(OrderSide.BUY, "100", "150.00")
        pos = Position(_instrument_id(), PositionId("P-001"), fill)
        self.cache.add_position(pos)

        pnl = self.portfolio.unrealized_pnl(_instrument_id(), Price("155.00", 2))
        assert pnl == Decimal("500.00")

    def test_realized_pnl_after_close(self):
        open_fill = _make_fill(OrderSide.BUY, "100", "150.00")
        pos = Position(_instrument_id(), PositionId("P-001"), open_fill)
        close_fill = _make_fill(OrderSide.SELL, "100", "160.00")
        pos.apply(close_fill)
        self.cache.add_position(pos)

        pnl = self.portfolio.realized_pnl(_instrument_id())
        assert pnl == Decimal("1000.00")

    def test_balance_total(self):
        venue = Venue("SIM")
        bal = self.portfolio.balance_total(venue)
        assert bal is not None
        assert bal.amount == Decimal("100000.00")
