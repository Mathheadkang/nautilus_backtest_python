#!/usr/bin/env python3
"""
Standalone example: backtest a mean-reversion strategy on synthetic
prediction-market data.  No API access or credentials needed.

Run:
    uv run python polymarket/example_backtest_synthetic.py
"""
from __future__ import annotations

import os
import random
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_core.backtest.engine import BacktestEngine
from nautilus_core.data import Bar, BarSpecification, BarType
from nautilus_core.enums import AccountType, BarAggregation, OmsType, PriceType
from nautilus_core.objects import Money, Price, Quantity

from polymarket.instruments import USDC, PredictionMarketOutcome
from polymarket.strategies import MeanReversionConfig, MeanReversionStrategy


def generate_ou_bars(instrument_id, num_bars=500, mu=0.55, theta=0.02, sigma=0.03, seed=42):
    """Generate Ornstein-Uhlenbeck process bars (mean-reverting probabilities)."""
    random.seed(seed)
    bar_spec = BarSpecification(60, BarAggregation.MINUTE, PriceType.MID)
    bar_type = BarType(instrument_id, bar_spec)
    base_ts = 1_700_000_000 * 1_000_000_000

    bars = []
    price = 0.50
    for i in range(num_bars):
        dp = theta * (mu - price) + sigma * random.gauss(0, 1)
        new_price = max(0.02, min(0.98, price + dp))

        high_px = min(0.99, max(price, new_price) + abs(random.gauss(0, sigma * 0.3)))
        low_px = max(0.01, min(price, new_price) - abs(random.gauss(0, sigma * 0.3)))
        ts = base_ts + i * 3_600_000_000_000

        bars.append(Bar(
            bar_type=bar_type,
            open=Price(price, 4),
            high=Price(high_px, 4),
            low=Price(low_px, 4),
            close=Price(new_price, 4),
            volume=Quantity(0, 0),
            ts_event=ts,
            ts_init=ts,
        ))
        price = new_price

    return bars, bar_type


def main():
    print("=" * 60)
    print("Polymarket Backtest — Mean Reversion on Synthetic Data")
    print("=" * 60)

    # Create instrument
    token_id = "0x" + "abcdef01" * 8
    instrument = PredictionMarketOutcome(
        token_id=token_id,
        market_question="Will BTC exceed $200k by end of 2026?",
        outcome_label="Yes",
        price_precision=4,
        size_precision=2,
    )

    # Generate data
    bars, bar_type = generate_ou_bars(instrument.id, num_bars=500, mu=0.55, sigma=0.025)
    print(f"\nData: {len(bars)} bars, price {bars[0].open} -> {bars[-1].close}")

    # Engine setup
    engine = BacktestEngine()
    engine.add_venue(
        venue_name="POLYMARKET",
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=USDC,
        starting_balances=[Money("10000", USDC)],
    )
    engine.add_instrument(instrument)
    engine.add_data(bars)

    # Strategy
    config = MeanReversionConfig(
        instrument_id=str(instrument.id),
        sma_period=20,
        entry_threshold=0.05,
        exit_threshold=0.02,
        trade_size=200,
        strategy_id="MeanRev-BTC200k",
    )
    strategy = MeanReversionStrategy(config)
    engine.add_strategy(strategy)
    strategy.subscribe_bars(bar_type)

    # Run
    print("\nRunning backtest...")
    engine.run()

    result = engine.get_result()
    print(result)

    # Position details
    positions = engine.cache.positions()
    closed = [p for p in positions if p.is_closed]
    open_pos = [p for p in positions if p.is_open]

    print(f"\nClosed positions: {len(closed)}")
    for p in closed[:5]:
        print(f"  {p.id}: PnL=${float(p.realized_pnl):,.2f}")

    if open_pos:
        print(f"\nOpen positions: {len(open_pos)}")
        for p in open_pos:
            print(f"  {p.id}: {p.side.name} {p.quantity} @ avg_open={p.avg_px_open:.4f}")


if __name__ == "__main__":
    main()
