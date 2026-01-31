from __future__ import annotations

from nautilus_core.data import Bar
from nautilus_core.enums import OrderSide
from nautilus_core.identifiers import InstrumentId
from nautilus_core.trading.config import StrategyConfig
from nautilus_core.trading.strategy import Strategy


class BuyAndHoldConfig(StrategyConfig):
    def __init__(
        self,
        instrument_id: str,
        trade_size: float = 100.0,
        strategy_id: str = "BuyAndHold",
    ) -> None:
        super().__init__(strategy_id=strategy_id)
        self.instrument_id_str = instrument_id
        self.trade_size = trade_size


class BuyAndHoldStrategy(Strategy):
    def __init__(self, config: BuyAndHoldConfig) -> None:
        super().__init__(config)
        self._config = config
        self.instrument_id: InstrumentId | None = None
        self._bought = False

    def on_start(self) -> None:
        self.instrument_id = InstrumentId.from_str(self._config.instrument_id_str)

    def on_bar(self, bar: Bar) -> None:
        if self._bought:
            return

        instrument = self.cache.instrument(self.instrument_id) if self.cache else None
        if instrument is None:
            return

        qty = instrument.make_qty(self._config.trade_size)
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            side=OrderSide.BUY,
            quantity=qty,
            ts_init=bar.ts_event,
        )
        self.submit_order(order)
        self._bought = True
