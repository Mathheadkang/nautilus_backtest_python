#!/usr/bin/env python3
"""
Standalone example: fetch real Polymarket data and backtest.

This requires internet access but NO credentials.
The Gamma API and CLOB prices-history endpoint are public.

Run:
    uv add requests
    uv run python polymarket/example_backtest_live_data.py

Optionally pass a market slug:
    uv run python polymarket/example_backtest_live_data.py --slug "will-trump-win-2024"
"""
from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_core.backtest.engine import BacktestEngine
from nautilus_core.enums import AccountType, OmsType
from nautilus_core.objects import Money

from polymarket.data_client import PolymarketDataClient
from polymarket.instruments import USDC, PredictionMarketOutcome
from polymarket.strategies import (
    MeanReversionConfig,
    MeanReversionStrategy,
    MomentumConfig,
    MomentumStrategy,
)


def main():
    parser = argparse.ArgumentParser(description="Backtest on real Polymarket data")
    parser.add_argument("--slug", type=str, default=None, help="Market slug from the URL")
    parser.add_argument("--fidelity", type=int, default=60, help="Price fidelity in minutes (default: 60)")
    parser.add_argument("--strategy", choices=["momentum", "meanrev"], default="momentum")
    args = parser.parse_args()

    client = PolymarketDataClient()

    # ── Find market ──────────────────────────────────────────────────
    if args.slug:
        print(f"Fetching market by slug: {args.slug}")
        market = client.get_market_by_slug(args.slug)
    else:
        print("Fetching top active market by volume...")
        markets = client.get_markets(limit=1, active=True, order="volume")
        if not markets:
            print("ERROR: No markets returned. Check your internet connection.")
            return
        market = markets[0]

    print(f"\nMarket:   {market.question}")
    print(f"Outcomes: {market.outcomes}")
    print(f"Prices:   {market.outcome_prices}")
    print(f"Volume:   ${market.volume:,.0f}")

    # ── Fetch historical data ────────────────────────────────────────
    token_id = market.yes_token_id
    print(f"\nFetching price history for YES token (fidelity={args.fidelity}min)...")

    bars = client.get_price_history_as_bars(
        token_id,
        interval="max",
        fidelity=args.fidelity,
    )
    if len(bars) < 20:
        print(f"Only {len(bars)} bars available. Try a different market or lower fidelity.")
        return

    print(f"Got {len(bars)} bars")
    print(f"Date range: {bars[0].ts_event} -> {bars[-1].ts_event}")
    print(f"Price range: {bars[0].close} -> {bars[-1].close}")

    # ── Create instrument ────────────────────────────────────────────
    instrument = PredictionMarketOutcome(
        token_id=token_id,
        market_question=market.question,
        outcome_label=market.outcomes[0] if market.outcomes else "Yes",
    )

    # ── Setup engine ─────────────────────────────────────────────────
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

    # ── Setup strategy ───────────────────────────────────────────────
    iid = str(instrument.id)

    if args.strategy == "momentum":
        config = MomentumConfig(
            instrument_id=iid,
            fast_period=5,
            slow_period=15,
            trade_size=100,
            strategy_id="Momentum",
        )
        strategy = MomentumStrategy(config)
    else:
        config = MeanReversionConfig(
            instrument_id=iid,
            sma_period=20,
            entry_threshold=0.05,
            exit_threshold=0.02,
            trade_size=100,
            strategy_id="MeanRev",
        )
        strategy = MeanReversionStrategy(config)

    engine.add_strategy(strategy)
    strategy.subscribe_bars(bars[0].bar_type)

    # ── Run ──────────────────────────────────────────────────────────
    print(f"\nRunning {args.strategy} strategy backtest...")
    engine.run()

    result = engine.get_result()
    print(result)

    # Summary
    positions = engine.cache.positions()
    orders = engine.cache.orders()
    print(f"\nTotal orders placed: {len(orders)}")
    print(f"Total positions: {len(positions)}")
    print(f"  Closed: {sum(1 for p in positions if p.is_closed)}")
    print(f"  Open:   {sum(1 for p in positions if p.is_open)}")


if __name__ == "__main__":
    main()
