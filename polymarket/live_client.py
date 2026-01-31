"""
Polymarket live trading client — wraps py-clob-client for authenticated
order placement, position management, and account queries.

Requires:  pip install py-clob-client
Docs:      https://docs.polymarket.com/developers/CLOB/clients/methods-overview
GitHub:    https://github.com/Polymarket/py-clob-client
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class PolymarketOrder:
    """Local representation of a placed order."""
    order_id: str
    token_id: str
    side: str      # "BUY" or "SELL"
    price: float
    size: float
    order_type: str  # "GTC", "FOK", "GTD"
    status: str


@dataclass
class PolymarketPosition:
    """A position in a prediction market outcome."""
    token_id: str
    outcome: str
    size: float
    avg_price: float
    market_question: str = ""


class PolymarketLiveClient:
    """
    Authenticated trading client for Polymarket.

    This wraps the official ``py-clob-client`` package.  Install it with::

        pip install py-clob-client

    Configuration is read from environment variables (see .env.example)
    or passed directly to the constructor.
    """

    def __init__(
        self,
        private_key: str | None = None,
        wallet_address: str | None = None,
        signature_type: int | None = None,
        clob_host: str | None = None,
        chain_id: int | None = None,
    ) -> None:
        self._private_key = private_key or os.environ.get("POLYMARKET_PRIVATE_KEY", "")
        self._wallet_address = wallet_address or os.environ.get("POLYMARKET_WALLET_ADDRESS", "")
        self._signature_type = (
            signature_type
            if signature_type is not None
            else int(os.environ.get("POLYMARKET_SIGNATURE_TYPE", "0"))
        )
        self._clob_host = clob_host or os.environ.get(
            "POLYMARKET_CLOB_HOST", "https://clob.polymarket.com"
        )
        self._chain_id = chain_id or int(os.environ.get("POLYMARKET_CHAIN_ID", "137"))

        self._client = None  # lazy init

    # ── Connection ────────────────────────────────────────────────────

    def connect(self) -> None:
        """Initialize the py-clob-client and derive API credentials."""
        try:
            from py_clob_client.client import ClobClient
        except ImportError:
            raise ImportError(
                "py-clob-client is required for live trading.\n"
                "Install it with:  pip install py-clob-client"
            )

        if not self._private_key:
            raise ValueError(
                "Private key is required. Set POLYMARKET_PRIVATE_KEY in your "
                "environment or pass it to the constructor."
            )

        self._client = ClobClient(
            self._clob_host,
            key=self._private_key,
            chain_id=self._chain_id,
            signature_type=self._signature_type,
            funder=self._wallet_address or None,
        )

        # Check if pre-set API creds exist in env
        api_key = os.environ.get("POLYMARKET_API_KEY")
        api_secret = os.environ.get("POLYMARKET_API_SECRET")
        api_passphrase = os.environ.get("POLYMARKET_API_PASSPHRASE")

        if api_key and api_secret and api_passphrase:
            from py_clob_client.clob_types import ApiCreds
            self._client.set_api_creds(ApiCreds(
                api_key=api_key,
                api_secret=api_secret,
                api_passphrase=api_passphrase,
            ))
        else:
            # Derive credentials from the private key
            creds = self._client.create_or_derive_api_creds()
            self._client.set_api_creds(creds)

    @property
    def client(self):
        """Access the underlying ClobClient (connect first)."""
        if self._client is None:
            raise RuntimeError("Call .connect() before using the client.")
        return self._client

    # ── Orders ────────────────────────────────────────────────────────

    def buy_market(self, token_id: str, amount: float) -> dict:
        """
        Place a market BUY order (fill-or-kill) for a dollar amount.

        Parameters
        ----------
        token_id : str
            The CLOB token ID for the outcome you want to buy.
        amount : float
            The USDC amount to spend.
        """
        from py_clob_client.clob_types import MarketOrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY

        args = MarketOrderArgs(
            token_id=token_id,
            amount=amount,
            side=BUY,
            order_type=OrderType.FOK,
        )
        signed = self.client.create_market_order(args)
        return self.client.post_order(signed, OrderType.FOK)

    def sell_market(self, token_id: str, amount: float) -> dict:
        """Place a market SELL order (fill-or-kill)."""
        from py_clob_client.clob_types import MarketOrderArgs, OrderType
        from py_clob_client.order_builder.constants import SELL

        args = MarketOrderArgs(
            token_id=token_id,
            amount=amount,
            side=SELL,
            order_type=OrderType.FOK,
        )
        signed = self.client.create_market_order(args)
        return self.client.post_order(signed, OrderType.FOK)

    def buy_limit(
        self, token_id: str, price: float, size: float, order_type: str = "GTC"
    ) -> dict:
        """
        Place a limit BUY order.

        Parameters
        ----------
        token_id : str
            CLOB token ID.
        price : float
            Limit price (0.01 – 0.99).
        size : float
            Number of shares.
        order_type : str
            "GTC" (default), "FOK", or "GTD".
        """
        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY

        ot = getattr(OrderType, order_type)
        args = OrderArgs(token_id=token_id, price=price, size=size, side=BUY)
        signed = self.client.create_order(args)
        return self.client.post_order(signed, ot)

    def sell_limit(
        self, token_id: str, price: float, size: float, order_type: str = "GTC"
    ) -> dict:
        """Place a limit SELL order."""
        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import SELL

        ot = getattr(OrderType, order_type)
        args = OrderArgs(token_id=token_id, price=price, size=size, side=SELL)
        signed = self.client.create_order(args)
        return self.client.post_order(signed, ot)

    def cancel_order(self, order_id: str) -> dict:
        """Cancel a single open order."""
        return self.client.cancel(order_id)

    def cancel_all_orders(self) -> dict:
        """Cancel all open orders."""
        return self.client.cancel_all()

    def get_open_orders(self) -> list[dict]:
        """Get all open orders for this account."""
        from py_clob_client.clob_types import OpenOrderParams
        return self.client.get_orders(OpenOrderParams())

    # ── Account info ──────────────────────────────────────────────────

    def get_trades(self) -> list[dict]:
        """Get recent trades for this account."""
        return self.client.get_trades()

    def get_last_trade_price(self, token_id: str) -> float:
        """Get the last trade price for a token."""
        result = self.client.get_last_trade_price(token_id)
        return float(result.get("price", 0))
