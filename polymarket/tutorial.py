#!/usr/bin/env python3
"""
=============================================================================
 POLYMARKET BACKTESTING & LIVE TRADING — COMPLETE TUTORIAL
=============================================================================

This tutorial walks you through:

  Part 1 — Fetching market data from Polymarket (no auth required)
  Part 2 — Running a backtest on historical prediction-market data
  Part 3 — Backtesting with synthetic data (offline / no API needed)
  Part 4 — Connecting for live trading (requires wallet + API key)
  Part 5 — Building your own strategy

Prerequisites:
    uv add requests py-clob-client python-dotenv

Run this file:
    uv run python polymarket/tutorial.py

Polymarket docs:
    https://docs.polymarket.com/
    https://github.com/Polymarket/py-clob-client

=============================================================================
"""
from __future__ import annotations

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PART 1 — Fetching Market Data (read-only, no auth)                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def part1_fetch_market_data():
    """
    The Polymarket API has two main services for reading data:

    1. **Gamma API** (https://gamma-api.polymarket.com)
       - Discover markets, get metadata (question, outcomes, token IDs)
       - No authentication required
       - Key endpoints: /markets, /events

    2. **CLOB API** (https://clob.polymarket.com)
       - Get historical prices, order books, midpoints
       - No auth for read endpoints
       - Key endpoint: /prices-history

    Every market has two outcome tokens (e.g. YES / NO), each identified by
    a long hex `token_id`.  Prices range from $0.01 to $0.99.  A YES token
    at $0.65 means "the market thinks there's a 65% chance this happens."
    """
    from polymarket.data_client import PolymarketDataClient

    client = PolymarketDataClient()

    # ── 1a. List top markets by volume ───────────────────────────────
    print("=" * 70)
    print("PART 1 — Fetching Market Data from Polymarket")
    print("=" * 70)

    print("\n📊 Fetching top 5 active markets by volume...")
    markets = client.get_markets(limit=5, active=True, order="volume")

    for i, m in enumerate(markets, 1):
        print(f"\n  [{i}] {m.question}")
        print(f"      Outcomes: {m.outcomes}")
        print(f"      Prices:   {m.outcome_prices}")
        print(f"      Volume:   ${m.volume:,.0f}")
        print(f"      YES token: {m.yes_token_id[:32]}...")
        print(f"      NO token:  {m.no_token_id[:32]}...")

    if not markets:
        print("  (no markets returned — you may be offline)")
        return None

    # ── 1b. Get price history for the top market ─────────────────────
    top_market = markets[0]
    token_id = top_market.yes_token_id

    print(f"\n📈 Fetching price history for: {top_market.question[:60]}...")
    history = client.get_price_history(token_id, interval="1w", fidelity=60)

    print(f"   Got {len(history)} price points")
    if history:
        print(f"   First: t={history[0].timestamp}, p={history[0].price:.4f}")
        print(f"   Last:  t={history[-1].timestamp}, p={history[-1].price:.4f}")

    return top_market


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PART 2 — Backtesting on Real Polymarket Data                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def part2_backtest_real_data(market=None):
    """
    Fetch real historical data from Polymarket and run a backtest.

    Flow:
      1. Use PolymarketDataClient to get price history
      2. Convert price history → Bar objects
      3. Create a PredictionMarketOutcome instrument
      4. Configure the backtest engine
      5. Add a strategy and run
    """
    from decimal import Decimal

    from nautilus_core.backtest.engine import BacktestEngine
    from nautilus_core.enums import AccountType, OmsType
    from nautilus_core.objects import Money

    from polymarket.data_client import PolymarketDataClient
    from polymarket.instruments import USDC, PredictionMarketOutcome
    from polymarket.strategies import MomentumConfig, MomentumStrategy

    print("\n" + "=" * 70)
    print("PART 2 — Backtesting on Real Polymarket Data")
    print("=" * 70)

    client = PolymarketDataClient()

    # If we already have a market from Part 1, use it
    if market is None:
        print("\n  Fetching a high-volume market...")
        markets = client.get_markets(limit=1, active=True, order="volume")
        if not markets:
            print("  Cannot reach API — skipping Part 2 (try Part 3 for offline)")
            return
        market = markets[0]

    token_id = market.yes_token_id
    print(f"\n  Market: {market.question[:70]}")
    print(f"  Token:  {token_id[:32]}...")

    # Fetch price history as Bar objects
    print("  Fetching historical prices (interval=max, fidelity=60)...")
    bars = client.get_price_history_as_bars(token_id, interval="max", fidelity=60)
    if len(bars) < 30:
        print(f"  Only {len(bars)} bars — not enough for a meaningful backtest.")
        print("  Try a more established market or Part 3 for synthetic data.")
        return

    print(f"  Got {len(bars)} hourly bars")

    # Create instrument
    instrument = PredictionMarketOutcome(
        token_id=token_id,
        market_question=market.question,
        outcome_label=market.outcomes[0] if market.outcomes else "Yes",
        price_precision=4,
        size_precision=2,
    )

    # Setup engine
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

    # Setup strategy
    config = MomentumConfig(
        instrument_id=str(instrument.id),
        fast_period=5,
        slow_period=15,
        trade_size=100,
        strategy_id="PolyMomentum",
    )
    strategy = MomentumStrategy(config)
    engine.add_strategy(strategy)
    strategy.subscribe_bars(bars[0].bar_type)

    # Run!
    print("\n  Running backtest...")
    engine.run()
    result = engine.get_result()
    print(result)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PART 3 — Backtesting with Synthetic Data (offline)                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def part3_backtest_synthetic():
    """
    Run a backtest without needing API access by generating synthetic
    prediction-market data.

    Prediction market prices are bounded [0, 1] so the synthetic data
    uses a mean-reverting process (Ornstein-Uhlenbeck) which is more
    realistic than a random walk for probabilities.
    """
    import math
    import random
    from decimal import Decimal

    from nautilus_core.backtest.engine import BacktestEngine
    from nautilus_core.data import Bar, BarSpecification, BarType
    from nautilus_core.enums import (
        AccountType,
        BarAggregation,
        OmsType,
        PriceType,
    )
    from nautilus_core.identifiers import InstrumentId, Symbol, Venue
    from nautilus_core.objects import Money, Price, Quantity

    from polymarket.instruments import USDC, PredictionMarketOutcome
    from polymarket.strategies import (
        MeanReversionConfig,
        MeanReversionStrategy,
        MomentumConfig,
        MomentumStrategy,
        ValueConfig,
        ValueStrategy,
    )

    print("\n" + "=" * 70)
    print("PART 3 — Backtesting with Synthetic Prediction-Market Data")
    print("=" * 70)

    # ── Generate synthetic prediction market data ────────────────────
    # Ornstein-Uhlenbeck process: mean-reverting around a central value
    random.seed(42)
    num_bars = 500
    mu = 0.55       # long-run mean (true probability)
    theta = 0.02    # mean reversion speed
    sigma = 0.03    # volatility
    price = 0.50    # starting price

    token_id = "0x" + "a1b2c3d4" * 8  # fake token ID
    instrument = PredictionMarketOutcome(
        token_id=token_id,
        market_question="Will event X happen by end of year?",
        outcome_label="Yes",
        price_precision=4,
        size_precision=2,
    )

    short_id = token_id[:16]
    instrument_id = instrument.id
    bar_spec = BarSpecification(60, BarAggregation.MINUTE, PriceType.MID)
    bar_type = BarType(instrument_id, bar_spec)

    base_ts = 1_700_000_000 * 1_000_000_000  # nanoseconds
    bars: list[Bar] = []

    for i in range(num_bars):
        # OU step
        dp = theta * (mu - price) + sigma * random.gauss(0, 1)
        new_price = max(0.02, min(0.98, price + dp))

        open_px = price
        close_px = new_price
        high_px = min(0.99, max(open_px, close_px) + abs(random.gauss(0, sigma * 0.3)))
        low_px = max(0.01, min(open_px, close_px) - abs(random.gauss(0, sigma * 0.3)))

        ts = base_ts + i * 3_600_000_000_000  # hourly

        bars.append(Bar(
            bar_type=bar_type,
            open=Price(open_px, 4),
            high=Price(high_px, 4),
            low=Price(low_px, 4),
            close=Price(close_px, 4),
            volume=Quantity(0, 0),
            ts_event=ts,
            ts_init=ts,
        ))
        price = new_price

    print(f"\n  Generated {len(bars)} synthetic bars")
    print(f"  Price range: {bars[0].open} -> {bars[-1].close}")
    print(f"  True probability (mu): {mu}")

    # ── Run three strategies ─────────────────────────────────────────

    strategies_configs = [
        ("Mean Reversion", MeanReversionStrategy, MeanReversionConfig(
            instrument_id=str(instrument_id),
            sma_period=20,
            entry_threshold=0.05,
            exit_threshold=0.02,
            trade_size=100,
            strategy_id="MeanRev",
        )),
        ("Momentum (EMA)", MomentumStrategy, MomentumConfig(
            instrument_id=str(instrument_id),
            fast_period=5,
            slow_period=15,
            trade_size=100,
            strategy_id="Momentum",
        )),
        ("Value (fair=0.55)", ValueStrategy, ValueConfig(
            instrument_id=str(instrument_id),
            fair_value=0.55,
            edge_threshold=0.08,
            trade_size=100,
            strategy_id="Value",
        )),
    ]

    for name, strategy_cls, config in strategies_configs:
        print(f"\n{'─' * 60}")
        print(f"  Strategy: {name}")
        print(f"{'─' * 60}")

        engine = BacktestEngine()
        engine.add_venue(
            venue_name="POLYMARKET",
            oms_type=OmsType.NETTING,
            account_type=AccountType.CASH,
            base_currency=USDC,
            starting_balances=[Money("10000", USDC)],
        )
        engine.add_instrument(instrument)
        engine.add_data(list(bars))  # copy since engine may modify

        strategy = strategy_cls(config)
        engine.add_strategy(strategy)
        strategy.subscribe_bars(bar_type)

        engine.run()
        result = engine.get_result()

        print(f"  Orders:   {result.total_orders}")
        print(f"  Fills:    {result.total_fills}")
        print(f"  PnL:      ${float(result.total_return):,.2f}")
        print(f"  Return:   {float(result.total_return / result.starting_balance * 100):.2f}%")
        print(f"  Drawdown: ${float(result.max_drawdown):,.2f}")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PART 4 — Live Trading (requires .env credentials)                      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def part4_live_trading_demo():
    """
    Demonstrates how to connect and trade on Polymarket.

    ⚠️  This will NOT place real orders unless you uncomment the trading
    lines.  It only demonstrates the connection and read operations.

    Setup:
      1. Copy .env.example to .env
      2. Fill in your POLYMARKET_PRIVATE_KEY and POLYMARKET_WALLET_ADDRESS
      3. Install: uv add py-clob-client python-dotenv
      4. Fund your wallet with USDC on Polygon
      5. Approve token allowances (see py-clob-client docs)
    """
    print("\n" + "=" * 70)
    print("PART 4 — Live Trading Setup")
    print("=" * 70)

    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("  Install python-dotenv:  uv add python-dotenv")

    pk = os.environ.get("POLYMARKET_PRIVATE_KEY", "")
    if not pk or pk == "your_private_key_here":
        print("""
  ┌─────────────────────────────────────────────────────────────────┐
  │  No credentials found.  To enable live trading:                │
  │                                                                │
  │  1. Copy .env.example → .env                                   │
  │  2. Set POLYMARKET_PRIVATE_KEY  (your Polygon wallet PK)       │
  │  3. Set POLYMARKET_WALLET_ADDRESS  (your wallet address)       │
  │  4. Make sure you have USDC on Polygon and allowances set      │
  │                                                                │
  │  See:  https://github.com/Polymarket/py-clob-client            │
  └─────────────────────────────────────────────────────────────────┘
        """)
        return

    from polymarket.live_client import PolymarketLiveClient
    from polymarket.data_client import PolymarketDataClient

    print("\n  Connecting to Polymarket...")
    live = PolymarketLiveClient()
    live.connect()
    print("  Connected!")

    # Fetch a market to trade
    data = PolymarketDataClient()
    markets = data.get_markets(limit=1, active=True, order="volume")
    if not markets:
        print("  No markets available")
        return

    market = markets[0]
    token_id = market.yes_token_id
    print(f"\n  Market: {market.question[:60]}")
    print(f"  YES price: {market.yes_price:.4f}")
    print(f"  NO price:  {market.no_price:.4f}")

    # Get live midpoint
    mid = data.get_midpoint(token_id)
    print(f"  Live midpoint: {mid:.4f}")

    # Show open orders
    orders = live.get_open_orders()
    print(f"\n  Open orders: {len(orders)}")

    # ── Example: place a limit buy (COMMENTED OUT for safety) ────────
    print("""
  ┌─────────────────────────────────────────────────────────────────┐
  │  To place a real order, uncomment the lines below.             │
  │                                                                │
  │  # Buy 10 YES shares at $0.50                                  │
  │  result = live.buy_limit(token_id, price=0.50, size=10.0)      │
  │  print(result)                                                 │
  │                                                                │
  │  # Market buy $5 worth of YES shares                           │
  │  result = live.buy_market(token_id, amount=5.0)                │
  │  print(result)                                                 │
  │                                                                │
  │  # Cancel all orders                                           │
  │  live.cancel_all_orders()                                      │
  └─────────────────────────────────────────────────────────────────┘
    """)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PART 5 — Building Your Own Strategy                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def part5_custom_strategy_guide():
    """
    How to build a custom Polymarket strategy.

    This prints a guide — the actual strategy template is below.
    """
    print("\n" + "=" * 70)
    print("PART 5 — Building Your Own Strategy")
    print("=" * 70)
    print("""
  STEP 1: Define a Config dataclass
  ──────────────────────────────────
  Extend StrategyConfig with your parameters:

    class MyConfig(StrategyConfig):
        def __init__(self, instrument_id, ...):
            super().__init__(strategy_id="MyStrategy")
            self.instrument_id_str = instrument_id
            # your params here

  STEP 2: Implement the Strategy
  ──────────────────────────────
  Override on_start(), on_bar(), and optionally on_stop():

    class MyStrategy(Strategy):
        def on_start(self):
            self.instrument_id = InstrumentId.from_str(...)

        def on_bar(self, bar: Bar):
            price = bar.close.as_double()

            # Your logic here — check indicators, signals, etc.

            # To buy:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                side=OrderSide.BUY,
                quantity=instrument.make_qty(100),
                ts_init=bar.ts_event,
            )
            self.submit_order(order)

            # To sell / close:
            self.close_all_positions(self.instrument_id)

  STEP 3: Wire it up
  ──────────────────
    engine = BacktestEngine()
    engine.add_venue("POLYMARKET", ...)
    engine.add_instrument(instrument)
    engine.add_data(bars)

    strategy = MyStrategy(config)
    engine.add_strategy(strategy)
    strategy.subscribe_bars(bar_type)

    engine.run()
    print(engine.get_result())

  STEP 4: Go live
  ───────────────
  Once your backtest results look good, use PolymarketLiveClient
  to place real orders with the same logic:

    live = PolymarketLiveClient()
    live.connect()
    live.buy_limit(token_id, price=0.50, size=10.0)

  Key tips for prediction markets:
  ─────────────────────────────────
  • Prices are probabilities (0.01 – 0.99), NOT stock prices
  • Mean-reversion works better than momentum in most markets
  • Account for the bid-ask spread (often 2-5 cents)
  • Markets resolve to $1.00 or $0.00 — factor this binary payoff
  • Liquidity varies wildly between markets
  • Check the resolution source and end date before trading
    """)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  MAIN — Run all parts                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Polymarket Backtesting Tutorial")
    parser.add_argument(
        "parts",
        nargs="*",
        default=["3", "5"],
        help="Which parts to run: 1=fetch data, 2=real backtest, 3=synthetic, 4=live, 5=guide (default: 3 5)",
    )
    args = parser.parse_args()

    market = None
    for part in args.parts:
        if part == "1":
            market = part1_fetch_market_data()
        elif part == "2":
            part2_backtest_real_data(market)
        elif part == "3":
            part3_backtest_synthetic()
        elif part == "4":
            part4_live_trading_demo()
        elif part == "5":
            part5_custom_strategy_guide()
        else:
            print(f"Unknown part: {part}")
