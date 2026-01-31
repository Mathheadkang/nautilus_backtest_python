from decimal import Decimal

import pytest

from nautilus_core.backtest.engine import BacktestEngine
from nautilus_core.data import Bar, BarSpecification, BarType
from nautilus_core.enums import (
    AccountType,
    AssetClass,
    BarAggregation,
    OmsType,
    OrderSide,
    PriceType,
)
from nautilus_core.identifiers import InstrumentId, Symbol, Venue
from nautilus_core.instruments import Equity
from nautilus_core.objects import USD, Money, Price, Quantity
from nautilus_core.trading.config import StrategyConfig
from nautilus_core.trading.strategy import Strategy


class SimpleTestStrategy(Strategy):
    """Buy on first bar, sell on 5th bar."""

    def __init__(self, instrument_id_str: str):
        super().__init__(StrategyConfig(strategy_id="TestStrategy"))
        self.instrument_id_str = instrument_id_str
        self.instrument_id: InstrumentId | None = None
        self.bar_count = 0

    def on_start(self):
        self.instrument_id = InstrumentId.from_str(self.instrument_id_str)

    def on_bar(self, bar: Bar):
        self.bar_count += 1
        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:
            return

        if self.bar_count == 1:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                side=OrderSide.BUY,
                quantity=instrument.make_qty(100),
                ts_init=bar.ts_event,
            )
            self.submit_order(order)
        elif self.bar_count == 5:
            self.close_all_positions(self.instrument_id, ts_init=bar.ts_event)


def _make_bars(instrument_id, n=10, start_price=100.0):
    bar_spec = BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST)
    bar_type = BarType(instrument_id, bar_spec)
    bars = []
    price = start_price
    for i in range(n):
        ts = (i + 1) * 60_000_000_000
        bars.append(Bar(
            bar_type=bar_type,
            open=Price(price, 2),
            high=Price(price * 1.01, 2),
            low=Price(price * 0.99, 2),
            close=Price(price * 1.005, 2),
            volume=Quantity(1000, 0),
            ts_event=ts,
            ts_init=ts,
        ))
        price = price * 1.005
    return bars, bar_type


class TestBacktestEngine:
    def test_basic_run(self):
        instrument_id = InstrumentId(Symbol("TEST"), Venue("SIM"))
        instrument = Equity(
            instrument_id=instrument_id,
            quote_currency=USD,
            price_precision=2,
            size_precision=0,
            taker_fee=Decimal("0.0001"),
        )

        bars, bar_type = _make_bars(instrument_id, n=10)

        engine = BacktestEngine()
        engine.add_venue(
            venue_name="SIM",
            oms_type=OmsType.NETTING,
            account_type=AccountType.CASH,
            base_currency=USD,
            starting_balances=[Money("100000", USD)],
        )
        engine.add_instrument(instrument)
        engine.add_data(bars)

        strategy = SimpleTestStrategy("TEST.SIM")
        engine.add_strategy(strategy)
        strategy.subscribe_bars(bar_type)

        engine.run()

        result = engine.get_result()
        assert result.total_orders >= 2  # buy + sell
        assert result.total_fills >= 2
        assert result.starting_balance == Decimal("100000.00")
        assert result.ending_balance != result.starting_balance  # something happened

    def test_no_data_no_error(self):
        engine = BacktestEngine()
        engine.add_venue("SIM", starting_balances=[Money("100000", USD)], base_currency=USD)
        strategy = SimpleTestStrategy("TEST.SIM")
        engine.add_strategy(strategy)
        engine.run()
        result = engine.get_result()
        assert result.total_orders == 0

    def test_result_has_balance_curve(self):
        instrument_id = InstrumentId(Symbol("TEST"), Venue("SIM"))
        instrument = Equity(
            instrument_id=instrument_id,
            quote_currency=USD,
            price_precision=2,
            size_precision=0,
        )
        bars, bar_type = _make_bars(instrument_id, n=10)

        engine = BacktestEngine()
        engine.add_venue("SIM", starting_balances=[Money("100000", USD)], base_currency=USD)
        engine.add_instrument(instrument)
        engine.add_data(bars)

        strategy = SimpleTestStrategy("TEST.SIM")
        engine.add_strategy(strategy)
        strategy.subscribe_bars(bar_type)
        engine.run()

        result = engine.get_result()
        assert len(result.balance_curve) > 0

    def test_positions_created(self):
        instrument_id = InstrumentId(Symbol("TEST"), Venue("SIM"))
        instrument = Equity(
            instrument_id=instrument_id,
            quote_currency=USD,
            price_precision=2,
            size_precision=0,
        )
        bars, bar_type = _make_bars(instrument_id, n=10)

        engine = BacktestEngine()
        engine.add_venue("SIM", oms_type=OmsType.NETTING, starting_balances=[Money("100000", USD)], base_currency=USD)
        engine.add_instrument(instrument)
        engine.add_data(bars)

        strategy = SimpleTestStrategy("TEST.SIM")
        engine.add_strategy(strategy)
        strategy.subscribe_bars(bar_type)
        engine.run()

        positions = engine.cache.positions()
        assert len(positions) >= 1
