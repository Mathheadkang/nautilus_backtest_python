"""Integration test: EMA cross strategy on synthetic trending data."""
from decimal import Decimal

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"))

from nautilus_core.backtest.engine import BacktestEngine
from nautilus_core.data import Bar, BarSpecification, BarType
from nautilus_core.enums import (
    AccountType,
    BarAggregation,
    OmsType,
    PriceType,
)
from nautilus_core.identifiers import InstrumentId, Symbol, Venue
from nautilus_core.instruments import Equity
from nautilus_core.objects import USD, Money, Price, Quantity

from ema_cross_strategy import EMACrossStrategy, EMACrossStrategyConfig


def _generate_trending_bars(bar_type, n=200, start=100.0, trend=0.001):
    """Generate bars with a clear upward trend so EMA cross fires."""
    import random
    random.seed(123)
    bars = []
    price = start
    for i in range(n):
        change = trend + random.gauss(0, 0.005)
        open_px = price
        close_px = price * (1 + change)
        high_px = max(open_px, close_px) * 1.002
        low_px = min(open_px, close_px) * 0.998
        ts = (i + 1) * 60_000_000_000
        bars.append(Bar(
            bar_type=bar_type,
            open=Price(open_px, 2),
            high=Price(high_px, 2),
            low=Price(low_px, 2),
            close=Price(close_px, 2),
            volume=Quantity(5000, 0),
            ts_event=ts,
            ts_init=ts,
        ))
        price = close_px
    return bars


class TestEMACrossIntegration:
    def test_ema_cross_generates_trades(self):
        instrument_id = InstrumentId(Symbol("AAPL"), Venue("SIM"))
        instrument = Equity(
            instrument_id=instrument_id,
            quote_currency=USD,
            price_precision=2,
            size_precision=0,
            taker_fee=Decimal("0.0002"),
        )

        bar_spec = BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST)
        bar_type = BarType(instrument_id, bar_spec)
        bars = _generate_trending_bars(bar_type, n=200, start=100.0, trend=0.001)

        engine = BacktestEngine()
        engine.add_venue(
            venue_name="SIM",
            oms_type=OmsType.NETTING,
            account_type=AccountType.CASH,
            base_currency=USD,
            starting_balances=[Money("1000000", USD)],
        )
        engine.add_instrument(instrument)
        engine.add_data(bars)

        config = EMACrossStrategyConfig(
            instrument_id="AAPL.SIM",
            bar_type=str(bar_type),
            fast_period=10,
            slow_period=30,
            trade_size=100,
            strategy_id="EMACross-Test",
        )
        strategy = EMACrossStrategy(config)
        engine.add_strategy(strategy)
        strategy.subscribe_bars(bar_type)

        engine.run()

        result = engine.get_result()
        # With 200 bars and trending data, the EMA cross should generate trades
        assert result.total_orders > 0, "Expected at least 1 order from EMA cross"
        assert result.total_fills > 0, "Expected at least 1 fill"

        # Should have some positions
        all_positions = engine.cache.positions()
        assert len(all_positions) > 0, "Expected at least 1 position"

        # Verify PnL calculations are sane
        for pos in all_positions:
            if pos.is_closed:
                # realized_pnl should be a real number (not NaN or inf)
                assert pos.realized_pnl == pos.realized_pnl  # not NaN

    def test_ema_cross_with_downtrend(self):
        """Verify strategy also trades in downtrend."""
        instrument_id = InstrumentId(Symbol("AAPL"), Venue("SIM"))
        instrument = Equity(
            instrument_id=instrument_id,
            quote_currency=USD,
            price_precision=2,
            size_precision=0,
        )

        bar_spec = BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST)
        bar_type = BarType(instrument_id, bar_spec)
        bars = _generate_trending_bars(bar_type, n=200, start=100.0, trend=-0.001)

        engine = BacktestEngine()
        engine.add_venue(
            venue_name="SIM",
            oms_type=OmsType.NETTING,
            starting_balances=[Money("1000000", USD)],
            base_currency=USD,
        )
        engine.add_instrument(instrument)
        engine.add_data(bars)

        config = EMACrossStrategyConfig(
            instrument_id="AAPL.SIM",
            bar_type=str(bar_type),
            fast_period=10,
            slow_period=30,
            trade_size=100,
            strategy_id="EMACross-Down",
        )
        strategy = EMACrossStrategy(config)
        engine.add_strategy(strategy)
        strategy.subscribe_bars(bar_type)

        engine.run()

        result = engine.get_result()
        assert result.total_orders > 0
