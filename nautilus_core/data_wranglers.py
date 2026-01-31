from __future__ import annotations

from decimal import Decimal

from nautilus_core.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_core.enums import OrderSide
from nautilus_core.identifiers import InstrumentId, TradeId
from nautilus_core.objects import Price, Quantity


class BarDataWrangler:
    def __init__(self, bar_type: BarType, price_precision: int = 8, size_precision: int = 8) -> None:
        self.bar_type = bar_type
        self.price_precision = price_precision
        self.size_precision = size_precision

    def from_dataframe(self, df) -> list[Bar]:
        bars = []
        for _, row in df.iterrows():
            ts = 0
            if hasattr(row, "name") and hasattr(row.name, "value"):
                # DatetimeIndex — nanoseconds
                ts = int(row.name.value)
            elif "timestamp" in row.index:
                ts = int(row["timestamp"])
            elif "ts_event" in row.index:
                ts = int(row["ts_event"])

            bar = Bar(
                bar_type=self.bar_type,
                open=Price(row["open"], self.price_precision),
                high=Price(row["high"], self.price_precision),
                low=Price(row["low"], self.price_precision),
                close=Price(row["close"], self.price_precision),
                volume=Quantity(row["volume"], self.size_precision),
                ts_event=ts,
                ts_init=ts,
            )
            bars.append(bar)
        return bars

    def from_csv(self, filepath: str) -> list[Bar]:
        import pandas as pd
        df = pd.read_csv(filepath, parse_dates=True, index_col=0)
        return self.from_dataframe(df)


class QuoteTickDataWrangler:
    def __init__(self, instrument_id: InstrumentId, price_precision: int = 8, size_precision: int = 8) -> None:
        self.instrument_id = instrument_id
        self.price_precision = price_precision
        self.size_precision = size_precision

    def from_dataframe(self, df) -> list[QuoteTick]:
        ticks = []
        for _, row in df.iterrows():
            ts = 0
            if hasattr(row, "name") and hasattr(row.name, "value"):
                ts = int(row.name.value)
            elif "timestamp" in row.index:
                ts = int(row["timestamp"])
            elif "ts_event" in row.index:
                ts = int(row["ts_event"])

            tick = QuoteTick(
                instrument_id=self.instrument_id,
                bid_price=Price(row["bid_price"], self.price_precision),
                ask_price=Price(row["ask_price"], self.price_precision),
                bid_size=Quantity(row["bid_size"], self.size_precision),
                ask_size=Quantity(row["ask_size"], self.size_precision),
                ts_event=ts,
                ts_init=ts,
            )
            ticks.append(tick)
        return ticks

    def from_csv(self, filepath: str) -> list[QuoteTick]:
        import pandas as pd
        df = pd.read_csv(filepath, parse_dates=True, index_col=0)
        return self.from_dataframe(df)


class TradeTickDataWrangler:
    def __init__(self, instrument_id: InstrumentId, price_precision: int = 8, size_precision: int = 8) -> None:
        self.instrument_id = instrument_id
        self.price_precision = price_precision
        self.size_precision = size_precision

    def from_dataframe(self, df) -> list[TradeTick]:
        ticks = []
        for _, row in df.iterrows():
            ts = 0
            if hasattr(row, "name") and hasattr(row.name, "value"):
                ts = int(row.name.value)
            elif "timestamp" in row.index:
                ts = int(row["timestamp"])
            elif "ts_event" in row.index:
                ts = int(row["ts_event"])

            tick = TradeTick(
                instrument_id=self.instrument_id,
                price=Price(row["price"], self.price_precision),
                size=Quantity(row["size"], self.size_precision),
                aggressor_side=OrderSide[row.get("aggressor_side", "BUY")],
                trade_id=TradeId(str(row.get("trade_id", ts))),
                ts_event=ts,
                ts_init=ts,
            )
            ticks.append(tick)
        return ticks

    def from_csv(self, filepath: str) -> list[TradeTick]:
        import pandas as pd
        df = pd.read_csv(filepath, parse_dates=True, index_col=0)
        return self.from_dataframe(df)
