#!/usr/bin/env python3
"""Complete backtest example with synthetic data."""
from __future__ import annotations

import math
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal

from nautilus_core.backtest.engine import BacktestEngine
from nautilus_core.data import Bar, BarSpecification, BarType
from nautilus_core.enums import (
    AccountType,
    AssetClass,
    BarAggregation,
    OmsType,
    PriceType,
)
from nautilus_core.identifiers import InstrumentId, Symbol, Venue
from nautilus_core.instruments import Equity
from nautilus_core.objects import USD, Money, Price, Quantity

from ema_cross_strategy import EMACrossStrategy, EMACrossStrategyConfig


def generate_synthetic_bars(
    bar_type: BarType,
    num_bars: int = 500,
    start_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.0001,
    price_precision: int = 2,
    size_precision: int = 0,
) -> list[Bar]:
    """Generate synthetic OHLCV bars with a trend + noise."""
    import random
    random.seed(42)

    bars = []
    price = start_price
    base_ts = 1_000_000_000_000_000_000  # 1e18 ns ~ some epoch

    for i in range(num_bars):
        # Random walk with drift
        change = random.gauss(trend, volatility)
        open_px = price
        close_px = price * (1 + change)

        # Generate intra-bar high/low
        intra_vol = abs(change) + volatility * 0.5
        high_px = max(open_px, close_px) * (1 + random.uniform(0, intra_vol))
        low_px = min(open_px, close_px) * (1 - random.uniform(0, intra_vol))

        volume = random.uniform(1000, 10000)

        ts = base_ts + i * 60_000_000_000  # 1-minute bars

        bar = Bar(
            bar_type=bar_type,
            open=Price(open_px, price_precision),
            high=Price(high_px, price_precision),
            low=Price(low_px, price_precision),
            close=Price(close_px, price_precision),
            volume=Quantity(volume, size_precision),
            ts_event=ts,
            ts_init=ts,
        )
        bars.append(bar)
        price = close_px

    return bars


def main():
    # --- Setup instrument ---
    venue = Venue("SIM")
    symbol = Symbol("AAPL")
    instrument_id = InstrumentId(symbol, venue)

    instrument = Equity(
        instrument_id=instrument_id,
        quote_currency=USD,
        price_precision=2,
        size_precision=0,
        maker_fee=Decimal("0.0001"),
        taker_fee=Decimal("0.0002"),
    )

    # --- Setup bar type ---
    bar_spec = BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST)
    bar_type = BarType(instrument_id, bar_spec)

    # --- Generate synthetic data ---
    print("Generating synthetic data...")
    bars = generate_synthetic_bars(
        bar_type=bar_type,
        num_bars=500,
        start_price=150.0,
        volatility=0.015,
        trend=0.0003,  # slight upward trend
        price_precision=2,
        size_precision=0,
    )
    print(f"  Generated {len(bars)} bars")
    print(f"  Price range: {bars[0].open} -> {bars[-1].close}")

    # --- Setup backtest engine ---
    engine = BacktestEngine(trader_id="BACKTESTER-001")

    engine.add_venue(
        venue_name="SIM",
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=USD,
        starting_balances=[Money("1000000", USD)],
    )

    engine.add_instrument(instrument)
    engine.add_data(bars)

    # --- Setup strategy ---
    config = EMACrossStrategyConfig(
        instrument_id="AAPL.SIM",
        bar_type=str(bar_type),
        fast_period=10,
        slow_period=30,
        trade_size=100,
        strategy_id="EMACross-001",
    )
    strategy = EMACrossStrategy(config)

    # Subscribe to bars
    engine.add_strategy(strategy)
    strategy.subscribe_bars(bar_type)

    # --- Run backtest ---
    print("\nRunning backtest...")
    engine.run()

    # --- Results ---
    result = engine.get_result()
    print(result)

    # Print some details
    all_orders = engine.cache.orders()
    all_positions = engine.cache.positions()

    print(f"\nOrder Details:")
    for order in all_orders[:10]:
        print(f"  {order}")
    if len(all_orders) > 10:
        print(f"  ... and {len(all_orders) - 10} more orders")

    print(f"\nPosition Details:")
    for pos in all_positions[:5]:
        status = "OPEN" if pos.is_open else "CLOSED"
        print(f"  {pos.id}: {pos.side.name} {pos.quantity} @ avg_open={pos.avg_px_open:.2f}, "
              f"realized_pnl={pos.realized_pnl:.2f}, status={status}")
    if len(all_positions) > 5:
        print(f"  ... and {len(all_positions) - 5} more positions")


if __name__ == "__main__":
    main()
