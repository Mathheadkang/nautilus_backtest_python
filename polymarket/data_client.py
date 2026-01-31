"""
Polymarket data client — fetches markets and historical prices from the
Gamma API and CLOB API.  No authentication required for read-only access.

Gamma API docs : https://docs.polymarket.com/developers/gamma-markets-api/overview
CLOB timeseries: https://docs.polymarket.com/developers/CLOB/timeseries
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PolymarketMarket:
    """Represents a single Polymarket market (one question, two outcomes)."""
    condition_id: str
    question: str
    slug: str
    outcomes: list[str]
    outcome_prices: list[float]
    clob_token_ids: list[str]
    active: bool
    closed: bool
    volume: float
    liquidity: float
    end_date: str
    description: str = ""
    # optional extras from the raw API
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def yes_token_id(self) -> str:
        """Token ID for the first outcome (usually 'Yes')."""
        return self.clob_token_ids[0] if self.clob_token_ids else ""

    @property
    def no_token_id(self) -> str:
        """Token ID for the second outcome (usually 'No')."""
        return self.clob_token_ids[1] if len(self.clob_token_ids) > 1 else ""

    @property
    def yes_price(self) -> float:
        return self.outcome_prices[0] if self.outcome_prices else 0.0

    @property
    def no_price(self) -> float:
        return self.outcome_prices[1] if len(self.outcome_prices) > 1 else 0.0


@dataclass
class PricePoint:
    """A single (timestamp, price) from the prices-history endpoint."""
    timestamp: int   # unix seconds
    price: float


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

GAMMA_HOST = "https://gamma-api.polymarket.com"
CLOB_HOST = "https://clob.polymarket.com"


class PolymarketDataClient:
    """Read-only client for Polymarket market data."""

    def __init__(
        self,
        gamma_host: str = GAMMA_HOST,
        clob_host: str = CLOB_HOST,
        request_timeout: int = 30,
    ) -> None:
        self.gamma_host = gamma_host.rstrip("/")
        self.clob_host = clob_host.rstrip("/")
        self.timeout = request_timeout
        self._session = requests.Session()

    # ── Gamma API — market discovery ──────────────────────────────────

    def get_markets(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        active: bool | None = True,
        closed: bool | None = None,
        order: str = "volume",
        ascending: bool = False,
    ) -> list[PolymarketMarket]:
        """Fetch a page of markets from the Gamma API."""
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }
        if active is not None:
            params["active"] = str(active).lower()
        if closed is not None:
            params["closed"] = str(closed).lower()

        resp = self._session.get(
            f"{self.gamma_host}/markets",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return [self._parse_market(m) for m in resp.json()]

    def get_market_by_slug(self, slug: str) -> PolymarketMarket:
        """Fetch a single market by its URL slug."""
        resp = self._session.get(
            f"{self.gamma_host}/markets/slug/{slug}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return self._parse_market(resp.json())

    def get_market_by_condition(self, condition_id: str) -> PolymarketMarket:
        """Fetch a single market by its condition ID."""
        resp = self._session.get(
            f"{self.gamma_host}/markets/{condition_id}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return self._parse_market(resp.json())

    def get_events(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        closed: bool = False,
        order: str = "id",
        ascending: bool = False,
    ) -> list[dict]:
        """Fetch events (groups of related markets) from Gamma."""
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
            "closed": str(closed).lower(),
        }
        resp = self._session.get(
            f"{self.gamma_host}/events",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def search_markets(self, query: str, limit: int = 20) -> list[PolymarketMarket]:
        """Search markets by keyword in the question text."""
        all_markets = self.get_markets(limit=limit, active=True)
        q = query.lower()
        return [m for m in all_markets if q in m.question.lower()]

    # ── CLOB API — historical prices ─────────────────────────────────

    def get_price_history(
        self,
        token_id: str,
        *,
        interval: str | None = None,
        start_ts: int | None = None,
        end_ts: int | None = None,
        fidelity: int | None = None,
    ) -> list[PricePoint]:
        """
        Fetch historical price data for a CLOB token.

        Parameters
        ----------
        token_id : str
            The CLOB token ID (get from market.yes_token_id / no_token_id).
        interval : str, optional
            Duration shorthand: '1m', '1h', '6h', '1d', '1w', 'max'.
            Mutually exclusive with start_ts/end_ts.
        start_ts : int, optional
            Unix timestamp (seconds) — start of range.
        end_ts : int, optional
            Unix timestamp (seconds) — end of range.
        fidelity : int, optional
            Resolution in minutes (e.g. 60 = hourly candles).
        """
        params: dict[str, Any] = {"market": token_id}
        if interval is not None:
            params["interval"] = interval
        if start_ts is not None:
            params["startTs"] = start_ts
        if end_ts is not None:
            params["endTs"] = end_ts
        if fidelity is not None:
            params["fidelity"] = fidelity

        resp = self._session.get(
            f"{self.clob_host}/prices-history",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        history = data.get("history", [])
        return [PricePoint(timestamp=pt["t"], price=pt["p"]) for pt in history]

    def get_price_history_as_bars(
        self,
        token_id: str,
        *,
        interval: str = "max",
        fidelity: int = 60,
    ):
        """
        Fetch price history and convert to Bar objects for backtesting.

        Returns a list of nautilus_core Bar objects.  Since prediction markets
        don't have true OHLCV, we synthesize them:
        - open/high/low/close are all the snapshot price
        - volume is set to 0 (not provided by this endpoint)

        For higher-fidelity backtesting, use the CLOB order book data
        or trade-tick data instead.
        """
        from nautilus_core.data import Bar, BarSpecification, BarType
        from nautilus_core.enums import BarAggregation, PriceType
        from nautilus_core.identifiers import InstrumentId, Symbol, Venue
        from nautilus_core.objects import Price, Quantity

        points = self.get_price_history(token_id, interval=interval, fidelity=fidelity)
        if not points:
            return []

        # Create a bar type keyed on the token_id
        short_id = token_id[:16]  # first 16 chars as symbol
        instrument_id = InstrumentId(Symbol(short_id), Venue("POLYMARKET"))
        bar_spec = BarSpecification(fidelity, BarAggregation.MINUTE, PriceType.MID)
        bar_type = BarType(instrument_id, bar_spec)

        bars: list[Bar] = []
        for i, pt in enumerate(points):
            px = Price(pt.price, 4)
            ts_ns = pt.timestamp * 1_000_000_000
            bars.append(Bar(
                bar_type=bar_type,
                open=px,
                high=px,
                low=px,
                close=px,
                volume=Quantity(0, 0),
                ts_event=ts_ns,
                ts_init=ts_ns,
            ))

        # Improve OHLC by using adjacent points to approximate intra-bar range
        for i in range(len(bars)):
            prices = [bars[i].close]
            if i > 0:
                prices.append(bars[i - 1].close)
            if i < len(bars) - 1:
                prices.append(bars[i + 1].close)
            high_val = max(p.as_double() for p in prices)
            low_val = min(p.as_double() for p in prices)
            bars[i] = Bar(
                bar_type=bar_type,
                open=bars[i - 1].close if i > 0 else bars[i].close,
                high=Price(high_val, 4),
                low=Price(low_val, 4),
                close=bars[i].close,
                volume=Quantity(0, 0),
                ts_event=bars[i].ts_event,
                ts_init=bars[i].ts_init,
            )

        return bars

    # ── CLOB API — live orderbook / price ─────────────────────────────

    def get_midpoint(self, token_id: str) -> float:
        """Get the current midpoint price for a token."""
        resp = self._session.get(
            f"{self.clob_host}/midpoint",
            params={"token_id": token_id},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return float(resp.json().get("mid", 0))

    def get_orderbook(self, token_id: str) -> dict:
        """Get the current order book for a token."""
        resp = self._session.get(
            f"{self.clob_host}/book",
            params={"token_id": token_id},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Internal ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_market(raw: dict) -> PolymarketMarket:
        """Parse a raw Gamma API market dict into a PolymarketMarket."""
        outcomes = raw.get("outcomes", "[]")
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)

        outcome_prices = raw.get("outcomePrices", "[]")
        if isinstance(outcome_prices, str):
            outcome_prices = json.loads(outcome_prices)
        outcome_prices = [float(p) for p in outcome_prices]

        clob_token_ids = raw.get("clobTokenIds", "[]")
        if isinstance(clob_token_ids, str):
            clob_token_ids = json.loads(clob_token_ids)

        return PolymarketMarket(
            condition_id=raw.get("conditionId", raw.get("condition_id", "")),
            question=raw.get("question", ""),
            slug=raw.get("slug", ""),
            outcomes=outcomes,
            outcome_prices=outcome_prices,
            clob_token_ids=clob_token_ids,
            active=raw.get("active", False),
            closed=raw.get("closed", False),
            volume=float(raw.get("volumeNum", raw.get("volume", 0)) or 0),
            liquidity=float(raw.get("liquidityNum", raw.get("liquidity", 0)) or 0),
            end_date=raw.get("endDate", ""),
            description=raw.get("description", ""),
            raw=raw,
        )
