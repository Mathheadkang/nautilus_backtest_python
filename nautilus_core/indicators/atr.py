from __future__ import annotations

from nautilus_core.data import Bar
from nautilus_core.indicators.base import Indicator


class AverageTrueRange(Indicator):
    def __init__(self, period: int) -> None:
        super().__init__(f"ATR({period})")
        self.period = period
        self.value: float = 0.0
        self._prev_close: float | None = None
        self._sum_tr: float = 0.0

    def handle_bar(self, bar: Bar) -> None:
        self.has_inputs = True
        self._count += 1

        high = bar.high.as_double()
        low = bar.low.as_double()
        close = bar.close.as_double()

        if self._prev_close is None:
            tr = high - low
        else:
            tr = max(
                high - low,
                abs(high - self._prev_close),
                abs(low - self._prev_close),
            )

        if self._count <= self.period:
            self._sum_tr += tr
            if self._count == self.period:
                self.value = self._sum_tr / self.period
                self.initialized = True
        else:
            self.value = (self.value * (self.period - 1) + tr) / self.period

        self._prev_close = close

    def reset(self) -> None:
        super().reset()
        self.value = 0.0
        self._prev_close = None
        self._sum_tr = 0.0
