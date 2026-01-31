from __future__ import annotations

from nautilus_core.data import Bar, BarType
from nautilus_core.enums import OrderSide
from nautilus_core.identifiers import InstrumentId
from nautilus_core.indicators.ema import ExponentialMovingAverage
from nautilus_core.objects import Quantity
from nautilus_core.trading.config import StrategyConfig
from nautilus_core.trading.strategy import Strategy


class EMACrossStrategyConfig(StrategyConfig):
    def __init__(
        self,
        instrument_id: str,
        bar_type: str,
        fast_period: int = 10,
        slow_period: int = 20,
        trade_size: float = 100.0,
        strategy_id: str = "EMACross",
    ) -> None:
        super().__init__(strategy_id=strategy_id)
        self.instrument_id_str = instrument_id
        self.bar_type_str = bar_type
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.trade_size = trade_size


class EMACrossStrategy(Strategy):
    def __init__(self, config: EMACrossStrategyConfig) -> None:
        super().__init__(config)
        self._config = config
        self.instrument_id: InstrumentId | None = None
        self.bar_type: BarType | None = None
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)

    def on_start(self) -> None:
        self.instrument_id = InstrumentId.from_str(self._config.instrument_id_str)

        # Parse bar type from data (we'll subscribe to whatever bar type is in the data)
        # The bar_type is set by the backtest engine when data is added
        # For now, we subscribe via the data that will be routed to us
        # We register indicators which will be updated when bars arrive

    def on_bar(self, bar: Bar) -> None:
        # Update indicators
        self.fast_ema.handle_bar(bar)
        self.slow_ema.handle_bar(bar)

        if not self.slow_ema.initialized:
            return

        instrument = self.cache.instrument(self.instrument_id) if self.cache else None
        if instrument is None:
            return

        # Get current position
        is_flat = self.portfolio.is_flat(self.instrument_id) if self.portfolio else True
        is_long = self.portfolio.is_net_long(self.instrument_id) if self.portfolio else False
        is_short = self.portfolio.is_net_short(self.instrument_id) if self.portfolio else False

        qty = instrument.make_qty(self._config.trade_size)

        # EMA crossover logic
        if self.fast_ema.value > self.slow_ema.value:
            # Bullish signal
            if is_flat or is_short:
                # Close short if any
                if is_short:
                    self.close_all_positions(self.instrument_id, ts_init=bar.ts_event)
                # Go long
                order = self.order_factory.market(
                    instrument_id=self.instrument_id,
                    side=OrderSide.BUY,
                    quantity=qty,
                    ts_init=bar.ts_event,
                )
                self.submit_order(order)

        elif self.fast_ema.value < self.slow_ema.value:
            # Bearish signal
            if is_flat or is_long:
                # Close long if any
                if is_long:
                    self.close_all_positions(self.instrument_id, ts_init=bar.ts_event)
                # Go short
                order = self.order_factory.market(
                    instrument_id=self.instrument_id,
                    side=OrderSide.SELL,
                    quantity=qty,
                    ts_init=bar.ts_event,
                )
                self.submit_order(order)

    def on_stop(self) -> None:
        if self.instrument_id:
            self.close_all_positions(self.instrument_id)
