from __future__ import annotations

from dataclasses import dataclass

from nautilus_core.enums import BarAggregation, OrderSide, PriceType
from nautilus_core.identifiers import InstrumentId, TradeId
from nautilus_core.objects import Price, Quantity


@dataclass(frozen=True)
class BarSpecification:
    step: int
    aggregation: BarAggregation
    price_type: PriceType

    def __repr__(self) -> str:
        return f"{self.step}-{self.aggregation.name}-{self.price_type.name}"

    def __str__(self) -> str:
        return repr(self)


@dataclass(frozen=True)
class BarType:
    instrument_id: InstrumentId
    bar_spec: BarSpecification

    def __repr__(self) -> str:
        return f"{self.instrument_id}-{self.bar_spec}"

    def __str__(self) -> str:
        return repr(self)


@dataclass
class Bar:
    bar_type: BarType
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity
    ts_event: int
    ts_init: int

    @classmethod
    def from_dict(cls, d: dict, bar_type: BarType) -> Bar:
        prec = bar_type.instrument_id.symbol  # use a default precision
        price_prec = 8
        vol_prec = 8
        return cls(
            bar_type=bar_type,
            open=Price(d["open"], price_prec),
            high=Price(d["high"], price_prec),
            low=Price(d["low"], price_prec),
            close=Price(d["close"], price_prec),
            volume=Quantity(d["volume"], vol_prec),
            ts_event=d.get("ts_event", 0),
            ts_init=d.get("ts_init", 0),
        )

    def to_dict(self) -> dict:
        return {
            "bar_type": str(self.bar_type),
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "volume": str(self.volume),
            "ts_event": self.ts_event,
            "ts_init": self.ts_init,
        }

    def __repr__(self) -> str:
        return (
            f"Bar({self.bar_type}, "
            f"o={self.open}, h={self.high}, l={self.low}, c={self.close}, "
            f"v={self.volume}, ts={self.ts_event})"
        )


@dataclass
class QuoteTick:
    instrument_id: InstrumentId
    bid_price: Price
    ask_price: Price
    bid_size: Quantity
    ask_size: Quantity
    ts_event: int
    ts_init: int

    @classmethod
    def from_dict(cls, d: dict) -> QuoteTick:
        price_prec = 8
        size_prec = 8
        return cls(
            instrument_id=InstrumentId.from_str(d["instrument_id"]),
            bid_price=Price(d["bid_price"], price_prec),
            ask_price=Price(d["ask_price"], price_prec),
            bid_size=Quantity(d["bid_size"], size_prec),
            ask_size=Quantity(d["ask_size"], size_prec),
            ts_event=d.get("ts_event", 0),
            ts_init=d.get("ts_init", 0),
        )

    def to_dict(self) -> dict:
        return {
            "instrument_id": str(self.instrument_id),
            "bid_price": str(self.bid_price),
            "ask_price": str(self.ask_price),
            "bid_size": str(self.bid_size),
            "ask_size": str(self.ask_size),
            "ts_event": self.ts_event,
            "ts_init": self.ts_init,
        }


@dataclass
class TradeTick:
    instrument_id: InstrumentId
    price: Price
    size: Quantity
    aggressor_side: OrderSide
    trade_id: TradeId
    ts_event: int
    ts_init: int

    @classmethod
    def from_dict(cls, d: dict) -> TradeTick:
        price_prec = 8
        size_prec = 8
        return cls(
            instrument_id=InstrumentId.from_str(d["instrument_id"]),
            price=Price(d["price"], price_prec),
            size=Quantity(d["size"], size_prec),
            aggressor_side=OrderSide[d["aggressor_side"]],
            trade_id=TradeId(d["trade_id"]),
            ts_event=d.get("ts_event", 0),
            ts_init=d.get("ts_init", 0),
        )

    def to_dict(self) -> dict:
        return {
            "instrument_id": str(self.instrument_id),
            "price": str(self.price),
            "size": str(self.size),
            "aggressor_side": self.aggressor_side.name,
            "trade_id": str(self.trade_id),
            "ts_event": self.ts_event,
            "ts_init": self.ts_init,
        }
