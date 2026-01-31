"""
Example prediction-market strategies for Polymarket backtesting.

These demonstrate common prediction-market trading patterns:
  1. MeanReversionStrategy — buy when price dips below a band, sell when above
  2. MomentumStrategy      — ride trends using EMA crossovers
  3. ValueStrategy          — buy underpriced outcomes based on a model signal
"""
from __future__ import annotations

from nautilus_core.data import Bar, BarType
from nautilus_core.enums import OrderSide
from nautilus_core.identifiers import InstrumentId
from nautilus_core.indicators.ema import ExponentialMovingAverage
from nautilus_core.indicators.sma import SimpleMovingAverage
from nautilus_core.objects import Quantity
from nautilus_core.trading.config import StrategyConfig
from nautilus_core.trading.strategy import Strategy


# ---------------------------------------------------------------------------
# 1.  Mean-Reversion Strategy
# ---------------------------------------------------------------------------

class MeanReversionConfig(StrategyConfig):
    def __init__(
        self,
        instrument_id: str,
        sma_period: int = 20,
        entry_threshold: float = 0.05,
        exit_threshold: float = 0.02,
        trade_size: float = 50.0,
        strategy_id: str = "MeanReversion",
    ) -> None:
        super().__init__(strategy_id=strategy_id)
        self.instrument_id_str = instrument_id
        self.sma_period = sma_period
        self.entry_threshold = entry_threshold  # buy when price < sma - threshold
        self.exit_threshold = exit_threshold    # sell when price > sma + threshold
        self.trade_size = trade_size


class MeanReversionStrategy(Strategy):
    """
    Buy when the outcome price drops below its moving average by a threshold.
    Sell when price reverts back above the mean.

    This exploits temporary over-reactions in prediction markets where
    sentiment swings push prices away from fair value.
    """

    def __init__(self, config: MeanReversionConfig) -> None:
        super().__init__(config)
        self._config = config
        self.instrument_id: InstrumentId | None = None
        self.sma = SimpleMovingAverage(config.sma_period)

    def on_start(self) -> None:
        self.instrument_id = InstrumentId.from_str(self._config.instrument_id_str)

    def on_bar(self, bar: Bar) -> None:
        self.sma.handle_bar(bar)
        if not self.sma.initialized:
            return

        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:
            return

        price = bar.close.as_double()
        mean = self.sma.value
        qty = instrument.make_qty(self._config.trade_size)

        is_flat = self.portfolio.is_flat(self.instrument_id)
        is_long = self.portfolio.is_net_long(self.instrument_id)

        # Entry: price significantly below mean → buy
        if is_flat and price < mean - self._config.entry_threshold:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                side=OrderSide.BUY,
                quantity=qty,
                ts_init=bar.ts_event,
            )
            self.submit_order(order)

        # Exit: price reverts above mean → sell
        elif is_long and price > mean + self._config.exit_threshold:
            self.close_all_positions(self.instrument_id, ts_init=bar.ts_event)


# ---------------------------------------------------------------------------
# 2.  Momentum Strategy (EMA crossover)
# ---------------------------------------------------------------------------

class MomentumConfig(StrategyConfig):
    def __init__(
        self,
        instrument_id: str,
        fast_period: int = 5,
        slow_period: int = 15,
        trade_size: float = 50.0,
        strategy_id: str = "Momentum",
    ) -> None:
        super().__init__(strategy_id=strategy_id)
        self.instrument_id_str = instrument_id
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.trade_size = trade_size


class MomentumStrategy(Strategy):
    """
    EMA crossover strategy adapted for prediction markets.

    - Buy YES tokens when fast EMA crosses above slow EMA (rising probability)
    - Sell when fast crosses below slow (falling probability)

    Works well when there's a clear directional move (e.g. an event
    becoming more/less likely over time).
    """

    def __init__(self, config: MomentumConfig) -> None:
        super().__init__(config)
        self._config = config
        self.instrument_id: InstrumentId | None = None
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)

    def on_start(self) -> None:
        self.instrument_id = InstrumentId.from_str(self._config.instrument_id_str)

    def on_bar(self, bar: Bar) -> None:
        self.fast_ema.handle_bar(bar)
        self.slow_ema.handle_bar(bar)
        if not self.slow_ema.initialized:
            return

        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:
            return

        qty = instrument.make_qty(self._config.trade_size)
        is_flat = self.portfolio.is_flat(self.instrument_id)
        is_long = self.portfolio.is_net_long(self.instrument_id)

        if self.fast_ema.value > self.slow_ema.value:
            if is_flat:
                order = self.order_factory.market(
                    instrument_id=self.instrument_id,
                    side=OrderSide.BUY,
                    quantity=qty,
                    ts_init=bar.ts_event,
                )
                self.submit_order(order)
        else:
            if is_long:
                self.close_all_positions(self.instrument_id, ts_init=bar.ts_event)


# ---------------------------------------------------------------------------
# 3.  Value Strategy (model-driven)
# ---------------------------------------------------------------------------

class ValueConfig(StrategyConfig):
    def __init__(
        self,
        instrument_id: str,
        fair_value: float = 0.60,
        edge_threshold: float = 0.10,
        trade_size: float = 50.0,
        strategy_id: str = "Value",
    ) -> None:
        super().__init__(strategy_id=strategy_id)
        self.instrument_id_str = instrument_id
        self.fair_value = fair_value          # your model's probability estimate
        self.edge_threshold = edge_threshold  # minimum edge to trade
        self.trade_size = trade_size


class ValueStrategy(Strategy):
    """
    Buy when market price is below your estimated fair value by at least
    the edge threshold, sell when overpriced.

    In practice, you'd replace `fair_value` with a dynamic signal from
    your own model (polls aggregation, news sentiment, etc.).
    """

    def __init__(self, config: ValueConfig) -> None:
        super().__init__(config)
        self._config = config
        self.instrument_id: InstrumentId | None = None

    def on_start(self) -> None:
        self.instrument_id = InstrumentId.from_str(self._config.instrument_id_str)

    def on_bar(self, bar: Bar) -> None:
        instrument = self.cache.instrument(self.instrument_id)
        if instrument is None:
            return

        price = bar.close.as_double()
        fair = self._config.fair_value
        edge = self._config.edge_threshold
        qty = instrument.make_qty(self._config.trade_size)

        is_flat = self.portfolio.is_flat(self.instrument_id)
        is_long = self.portfolio.is_net_long(self.instrument_id)

        # Buy if market price is significantly below fair value
        if is_flat and price < fair - edge:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                side=OrderSide.BUY,
                quantity=qty,
                ts_init=bar.ts_event,
            )
            self.submit_order(order)

        # Sell if price reaches or exceeds fair value
        elif is_long and price >= fair:
            self.close_all_positions(self.instrument_id, ts_init=bar.ts_event)
