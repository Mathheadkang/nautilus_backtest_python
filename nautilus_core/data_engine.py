from __future__ import annotations

from typing import Any

from nautilus_core.cache import Cache
from nautilus_core.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_core.identifiers import InstrumentId
from nautilus_core.msgbus import MessageBus


class DataEngine:
    def __init__(self, cache: Cache, msgbus: MessageBus) -> None:
        self._cache = cache
        self._msgbus = msgbus
        self._bar_subscriptions: dict[BarType, bool] = {}
        self._quote_subscriptions: dict[InstrumentId, bool] = {}
        self._trade_subscriptions: dict[InstrumentId, bool] = {}

    def subscribe_bars(self, bar_type: BarType) -> None:
        self._bar_subscriptions[bar_type] = True

    def unsubscribe_bars(self, bar_type: BarType) -> None:
        self._bar_subscriptions.pop(bar_type, None)

    def subscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        self._quote_subscriptions[instrument_id] = True

    def unsubscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        self._quote_subscriptions.pop(instrument_id, None)

    def subscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        self._trade_subscriptions[instrument_id] = True

    def unsubscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        self._trade_subscriptions.pop(instrument_id, None)

    def process_bar(self, bar: Bar) -> None:
        self._cache.add_bar(bar)
        topic = f"data.bars.{bar.bar_type}"
        self._msgbus.publish(topic, bar)

    def process_quote_tick(self, tick: QuoteTick) -> None:
        self._cache.add_quote_tick(tick)
        topic = f"data.quotes.{tick.instrument_id}"
        self._msgbus.publish(topic, tick)

    def process_trade_tick(self, tick: TradeTick) -> None:
        self._cache.add_trade_tick(tick)
        topic = f"data.trades.{tick.instrument_id}"
        self._msgbus.publish(topic, tick)
