#!/usr/bin/env python3
"""
Standalone example: live trading on Polymarket.

⚠️  THIS WILL PLACE REAL ORDERS WITH REAL MONEY.
    Review the code carefully before running.

Prerequisites:
    1. Copy .env.example → .env and fill in your credentials
    2. Install:  uv add py-clob-client python-dotenv requests
    3. Fund your Polygon wallet with USDC
    4. Set token allowances (one-time, see py-clob-client docs)

Run:
    uv run python polymarket/example_live_trading.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # ── Load .env ────────────────────────────────────────────────────
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Install python-dotenv:  uv add python-dotenv")
        print("Or set environment variables manually.")

    pk = os.environ.get("POLYMARKET_PRIVATE_KEY", "")
    if not pk or pk == "your_private_key_here":
        print("""
ERROR: No credentials configured.

  1. Copy .env.example → .env
  2. Set POLYMARKET_PRIVATE_KEY   (your Polygon wallet private key)
  3. Set POLYMARKET_WALLET_ADDRESS (your wallet address)

  See .env.example for all available settings.
        """)
        return

    from polymarket.data_client import PolymarketDataClient
    from polymarket.live_client import PolymarketLiveClient

    # ── Connect ──────────────────────────────────────────────────────
    print("Connecting to Polymarket...")
    live = PolymarketLiveClient()
    live.connect()
    print("Connected!\n")

    data = PolymarketDataClient()

    # ── Browse markets ───────────────────────────────────────────────
    print("Top 5 active markets:")
    markets = data.get_markets(limit=5, active=True, order="volume")
    for i, m in enumerate(markets, 1):
        yes_price = m.yes_price
        print(f"  [{i}] {m.question[:60]}")
        print(f"      YES: ${yes_price:.2f}  |  Volume: ${m.volume:,.0f}")

    if not markets:
        print("  No markets found.")
        return

    # ── Select a market ──────────────────────────────────────────────
    print("\nSelect a market number (or press Enter for #1): ", end="")
    choice = input().strip()
    idx = int(choice) - 1 if choice.isdigit() else 0
    idx = max(0, min(idx, len(markets) - 1))
    market = markets[idx]

    print(f"\nSelected: {market.question}")
    print(f"  Outcomes: {market.outcomes}")
    print(f"  Prices:   YES=${market.yes_price:.4f}  NO=${market.no_price:.4f}")

    token_id = market.yes_token_id

    # ── Get live orderbook ───────────────────────────────────────────
    mid = data.get_midpoint(token_id)
    print(f"  Midpoint: ${mid:.4f}")

    book = data.get_orderbook(token_id)
    bids = book.get("bids", [])[:3]
    asks = book.get("asks", [])[:3]
    print(f"\n  Order Book (top 3):")
    print(f"    {'BIDS':>20s}  |  {'ASKS':<20s}")
    for i in range(max(len(bids), len(asks))):
        bid_str = f"{bids[i]['price']} x {bids[i]['size']}" if i < len(bids) else ""
        ask_str = f"{asks[i]['price']} x {asks[i]['size']}" if i < len(asks) else ""
        print(f"    {bid_str:>20s}  |  {ask_str:<20s}")

    # ── Show open orders ─────────────────────────────────────────────
    orders = live.get_open_orders()
    print(f"\n  Your open orders: {len(orders)}")
    for o in orders[:5]:
        print(f"    {o.get('side', '?')} {o.get('size', '?')} @ {o.get('price', '?')}")

    # ── Place an order ───────────────────────────────────────────────
    print(f"""
┌──────────────────────────────────────────────────────────────────┐
│  Ready to trade. Example commands:                               │
│                                                                  │
│  BUY 10 YES shares at $0.50:                                     │
│    result = live.buy_limit("{token_id[:20]}...", 0.50, 10.0)     │
│                                                                  │
│  SELL (market order) $5 worth:                                   │
│    result = live.sell_market("{token_id[:20]}...", 5.0)           │
│                                                                  │
│  Cancel all orders:                                              │
│    live.cancel_all_orders()                                      │
└──────────────────────────────────────────────────────────────────┘
    """)

    print("Enter action (buy/sell/cancel/quit): ", end="")
    action = input().strip().lower()

    if action == "buy":
        print("  Price (e.g. 0.50): ", end="")
        price = float(input().strip())
        print("  Size (shares, e.g. 10): ", end="")
        size = float(input().strip())

        print(f"\n  Placing limit BUY {size} shares @ ${price:.2f}...")
        result = live.buy_limit(token_id, price=price, size=size)
        print(f"  Result: {result}")

    elif action == "sell":
        print("  Price (e.g. 0.60): ", end="")
        price = float(input().strip())
        print("  Size (shares, e.g. 10): ", end="")
        size = float(input().strip())

        print(f"\n  Placing limit SELL {size} shares @ ${price:.2f}...")
        result = live.sell_limit(token_id, price=price, size=size)
        print(f"  Result: {result}")

    elif action == "cancel":
        print("  Cancelling all orders...")
        result = live.cancel_all_orders()
        print(f"  Result: {result}")

    elif action == "quit":
        print("  Bye!")
    else:
        print(f"  Unknown action: {action}")


if __name__ == "__main__":
    main()
