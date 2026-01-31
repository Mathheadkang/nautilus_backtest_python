"""
Polymarket-specific instrument definitions.

A Polymarket market is modeled as two instruments — one for each outcome
(YES and NO).  Prices range from $0.00 to $1.00, representing implied
probability.
"""
from __future__ import annotations

from decimal import Decimal

from nautilus_core.enums import AssetClass
from nautilus_core.identifiers import InstrumentId, Symbol, Venue
from nautilus_core.instruments import Instrument
from nautilus_core.objects import USDT, Currency, Price, Quantity


# Polymarket settles in USDC on Polygon, but for our model we use USDT
# as a stand-in (same precision).  Replace with a proper USDC definition
# if you want exact labeling.
USDC = Currency("USDC", 2, USDT.currency_type)

POLYMARKET_VENUE = Venue("POLYMARKET")


class PredictionMarketOutcome(Instrument):
    """
    A single outcome token in a prediction market.

    Prices are between 0.00 and 1.00 (probability).
    Each share pays $1.00 if the outcome resolves YES, $0.00 otherwise.
    """

    def __init__(
        self,
        token_id: str,
        market_question: str,
        outcome_label: str,
        *,
        price_precision: int = 4,
        size_precision: int = 2,
        maker_fee: Decimal = Decimal("0"),
        taker_fee: Decimal = Decimal("0"),
    ) -> None:
        # Use a shortened token ID as the symbol for readability
        short_id = token_id[:16]
        symbol = Symbol(short_id)
        instrument_id = InstrumentId(symbol, POLYMARKET_VENUE)

        super().__init__(
            instrument_id=instrument_id,
            asset_class=AssetClass.INDEX,  # prediction markets are closest to index
            quote_currency=USDC,
            price_precision=price_precision,
            size_precision=size_precision,
            price_increment=Price(Decimal(10) ** -price_precision, price_precision),
            size_increment=Quantity(Decimal(10) ** -size_precision, size_precision),
            min_price=Price("0.01", price_precision),
            max_price=Price("0.99", price_precision),
            maker_fee=maker_fee,
            taker_fee=taker_fee,
        )

        self.token_id = token_id
        self.market_question = market_question
        self.outcome_label = outcome_label

    def __repr__(self) -> str:
        return (
            f"PredictionMarketOutcome("
            f"'{self.outcome_label}' for '{self.market_question[:50]}...', "
            f"token={self.token_id[:16]}...)"
        )


def create_instruments_from_market(market) -> tuple[PredictionMarketOutcome, PredictionMarketOutcome]:
    """
    Create a pair of (YES, NO) instruments from a PolymarketMarket object.

    Parameters
    ----------
    market : PolymarketMarket
        A market object from the data client.

    Returns
    -------
    (yes_instrument, no_instrument)
    """
    yes = PredictionMarketOutcome(
        token_id=market.yes_token_id,
        market_question=market.question,
        outcome_label=market.outcomes[0] if market.outcomes else "Yes",
    )
    no = PredictionMarketOutcome(
        token_id=market.no_token_id,
        market_question=market.question,
        outcome_label=market.outcomes[1] if len(market.outcomes) > 1 else "No",
    )
    return yes, no
