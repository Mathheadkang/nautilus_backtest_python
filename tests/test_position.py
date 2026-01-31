from decimal import Decimal

import pytest

from nautilus_core.enums import OrderSide, OrderType, PositionSide
from nautilus_core.events import OrderFilled
from nautilus_core.identifiers import (
    AccountId,
    ClientOrderId,
    InstrumentId,
    PositionId,
    Symbol,
    TradeId,
    Venue,
    VenueOrderId,
    StrategyId,
    TraderId,
)
from nautilus_core.objects import USD, Money, Price, Quantity
from nautilus_core.position import Position


def _make_fill(side: OrderSide, qty: str, px: str, commission: str = "0.00") -> OrderFilled:
    return OrderFilled(
        trader_id=TraderId("TESTER-001"),
        strategy_id=StrategyId("S-001"),
        instrument_id=InstrumentId(Symbol("AAPL"), Venue("SIM")),
        client_order_id=ClientOrderId("O-001"),
        venue_order_id=VenueOrderId("V-001"),
        account_id=AccountId("SIM-001"),
        trade_id=TradeId("T-001"),
        order_side=side,
        order_type=OrderType.MARKET,
        last_qty=Quantity(qty, 0),
        last_px=Price(px, 2),
        currency=USD,
        commission=Money(commission, USD),
    )


class TestPosition:
    def test_open_long(self):
        fill = _make_fill(OrderSide.BUY, "100", "150.00")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            fill,
        )
        assert pos.side == PositionSide.LONG
        assert pos.is_open
        assert pos.is_long
        assert not pos.is_short
        assert pos.quantity == Quantity("100", 0)
        assert pos.avg_px_open == Decimal("150.00")

    def test_open_short(self):
        fill = _make_fill(OrderSide.SELL, "100", "150.00")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            fill,
        )
        assert pos.side == PositionSide.SHORT
        assert pos.is_short
        assert pos.quantity == Quantity("100", 0)

    def test_close_long_pnl(self):
        # Open long at 150
        open_fill = _make_fill(OrderSide.BUY, "100", "150.00", "1.50")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            open_fill,
        )

        # Close at 160 => profit of (160-150) * 100 = 1000
        close_fill = _make_fill(OrderSide.SELL, "100", "160.00", "1.60")
        pos.apply(close_fill)

        assert pos.side == PositionSide.FLAT
        assert pos.is_closed
        assert pos.realized_pnl == Decimal("1000.00")
        assert pos.commissions[USD] == Decimal("3.10")

    def test_close_short_pnl(self):
        # Open short at 150
        open_fill = _make_fill(OrderSide.SELL, "100", "150.00")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            open_fill,
        )

        # Close at 140 => profit of (150-140) * 100 = 1000
        close_fill = _make_fill(OrderSide.BUY, "100", "140.00")
        pos.apply(close_fill)

        assert pos.is_closed
        assert pos.realized_pnl == Decimal("1000.00")

    def test_unrealized_pnl_long(self):
        fill = _make_fill(OrderSide.BUY, "100", "150.00")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            fill,
        )
        # Last price at 155 => unrealized = (155-150) * 100 = 500
        unrealized = pos.unrealized_pnl(Price("155.00", 2))
        assert unrealized == Decimal("500.00")

    def test_unrealized_pnl_short(self):
        fill = _make_fill(OrderSide.SELL, "100", "150.00")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            fill,
        )
        # Last price at 145 => unrealized = (150-145) * 100 = 500
        unrealized = pos.unrealized_pnl(Price("145.00", 2))
        assert unrealized == Decimal("500.00")

    def test_total_pnl(self):
        # Open at 150, partial close at 160, then check total with last at 155
        open_fill = _make_fill(OrderSide.BUY, "100", "150.00")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            open_fill,
        )
        partial_close = _make_fill(OrderSide.SELL, "50", "160.00")
        pos.apply(partial_close)

        assert pos.realized_pnl == Decimal("500.00")  # (160-150)*50
        assert pos.quantity == Quantity("50", 0)

        total = pos.total_pnl(Price("155.00", 2))
        # realized = 500 + unrealized = (155-150)*50 = 250 => 750
        assert total == Decimal("750.00")

    def test_notional_value(self):
        fill = _make_fill(OrderSide.BUY, "100", "150.00")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            fill,
        )
        notional = pos.notional_value(Price("155.00", 2))
        assert notional == Decimal("15500.00")

    def test_flat_position_unrealized_pnl_zero(self):
        fill = _make_fill(OrderSide.BUY, "100", "150.00")
        pos = Position(
            InstrumentId(Symbol("AAPL"), Venue("SIM")),
            PositionId("P-001"),
            fill,
        )
        close_fill = _make_fill(OrderSide.SELL, "100", "160.00")
        pos.apply(close_fill)
        assert pos.unrealized_pnl(Price("200.00", 2)) == Decimal("0")
