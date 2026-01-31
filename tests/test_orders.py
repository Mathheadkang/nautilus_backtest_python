from decimal import Decimal

import pytest

from nautilus_core.enums import OrderSide, OrderStatus, OrderType, TimeInForce
from nautilus_core.events import (
    OrderAccepted,
    OrderCanceled,
    OrderDenied,
    OrderFilled,
    OrderInitialized,
    OrderRejected,
    OrderSubmitted,
)
from nautilus_core.identifiers import (
    AccountId,
    ClientOrderId,
    InstrumentId,
    StrategyId,
    Symbol,
    TradeId,
    TraderId,
    Venue,
    VenueOrderId,
)
from nautilus_core.objects import USD, Money, Price, Quantity
from nautilus_core.orders import LimitOrder, MarketOrder, StopMarketOrder


def _make_instrument_id():
    return InstrumentId(Symbol("AAPL"), Venue("SIM"))


def _make_market_order_init(**kwargs):
    defaults = dict(
        trader_id=TraderId("TESTER-001"),
        strategy_id=StrategyId("S-001"),
        instrument_id=_make_instrument_id(),
        client_order_id=ClientOrderId("O-001"),
        order_side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Quantity("100", 0),
        time_in_force=TimeInForce.GTC,
    )
    defaults.update(kwargs)
    return OrderInitialized(**defaults)


class TestMarketOrder:
    def test_creation(self):
        init = _make_market_order_init()
        order = MarketOrder(init)
        assert order.status == OrderStatus.INITIALIZED
        assert order.side == OrderSide.BUY
        assert order.quantity == Quantity("100", 0)
        assert order.filled_qty == Quantity("0", 0)

    def test_submit_accept_fill_lifecycle(self):
        init = _make_market_order_init()
        order = MarketOrder(init)

        # Submit
        submitted = OrderSubmitted(client_order_id=order.client_order_id)
        order.apply(submitted)
        assert order.status == OrderStatus.SUBMITTED

        # Accept
        accepted = OrderAccepted(
            client_order_id=order.client_order_id,
            venue_order_id=VenueOrderId("V-001"),
        )
        order.apply(accepted)
        assert order.status == OrderStatus.ACCEPTED
        assert order.venue_order_id == VenueOrderId("V-001")

        # Fill
        filled = OrderFilled(
            client_order_id=order.client_order_id,
            venue_order_id=VenueOrderId("V-001"),
            trade_id=TradeId("T-001"),
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            last_qty=Quantity("100", 0),
            last_px=Price("150.00", 2),
            currency=USD,
            commission=Money("0.30", USD),
        )
        order.apply(filled)
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == Quantity("100", 0)
        assert order.leaves_qty == Quantity("0", 0)
        assert order.avg_px == Decimal("150.00")

    def test_denied(self):
        init = _make_market_order_init()
        order = MarketOrder(init)
        denied = OrderDenied(client_order_id=order.client_order_id, reason="No funds")
        order.apply(denied)
        assert order.status == OrderStatus.DENIED

    def test_rejected(self):
        init = _make_market_order_init()
        order = MarketOrder(init)
        order.apply(OrderSubmitted(client_order_id=order.client_order_id))
        rejected = OrderRejected(client_order_id=order.client_order_id, reason="Invalid")
        order.apply(rejected)
        assert order.status == OrderStatus.REJECTED

    def test_invalid_transition_raises(self):
        init = _make_market_order_init()
        order = MarketOrder(init)
        with pytest.raises(RuntimeError, match="Invalid order state transition"):
            order.apply(OrderAccepted(client_order_id=order.client_order_id))

    def test_partial_fill(self):
        init = _make_market_order_init()
        order = MarketOrder(init)
        order.apply(OrderSubmitted(client_order_id=order.client_order_id))
        order.apply(OrderAccepted(client_order_id=order.client_order_id, venue_order_id=VenueOrderId("V-001")))

        # Partial fill
        filled1 = OrderFilled(
            client_order_id=order.client_order_id,
            trade_id=TradeId("T-001"),
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            last_qty=Quantity("60", 0),
            last_px=Price("150.00", 2),
            currency=USD,
            commission=Money("0.18", USD),
        )
        order.apply(filled1)
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_qty == Quantity("60", 0)
        assert order.leaves_qty == Quantity("40", 0)

        # Complete fill
        filled2 = OrderFilled(
            client_order_id=order.client_order_id,
            trade_id=TradeId("T-002"),
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            last_qty=Quantity("40", 0),
            last_px=Price("151.00", 2),
            currency=USD,
            commission=Money("0.12", USD),
        )
        order.apply(filled2)
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == Quantity("100", 0)


class TestLimitOrder:
    def test_creation(self):
        init = OrderInitialized(
            trader_id=TraderId("TESTER-001"),
            strategy_id=StrategyId("S-001"),
            instrument_id=_make_instrument_id(),
            client_order_id=ClientOrderId("O-002"),
            order_side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Quantity("100", 0),
            price=Price("149.00", 2),
        )
        order = LimitOrder(init)
        assert order.price == Price("149.00", 2)
        assert order.order_type == OrderType.LIMIT

    def test_limit_requires_price(self):
        init = OrderInitialized(
            trader_id=TraderId("TESTER-001"),
            strategy_id=StrategyId("S-001"),
            instrument_id=_make_instrument_id(),
            client_order_id=ClientOrderId("O-003"),
            order_side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Quantity("100", 0),
        )
        with pytest.raises(ValueError, match="requires a price"):
            LimitOrder(init)


class TestStopMarketOrder:
    def test_creation(self):
        init = OrderInitialized(
            trader_id=TraderId("TESTER-001"),
            strategy_id=StrategyId("S-001"),
            instrument_id=_make_instrument_id(),
            client_order_id=ClientOrderId("O-004"),
            order_side=OrderSide.SELL,
            order_type=OrderType.STOP_MARKET,
            quantity=Quantity("50", 0),
            trigger_price=Price("145.00", 2),
        )
        order = StopMarketOrder(init)
        assert order.trigger_price == Price("145.00", 2)
