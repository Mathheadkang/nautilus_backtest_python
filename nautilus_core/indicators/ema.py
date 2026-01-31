from __future__ import annotations

from nautilus_core.data import Bar
from nautilus_core.indicators.base import Indicator


class ExponentialMovingAverage(Indicator):
    def __init__(self, period: int) -> None:
        super().__init__(f"EMA({period})")
        self.period = period
        self.value: float = 0.0
        self._multiplier = 2.0 / (period + 1.0)

    def handle_bar(self, bar: Bar) -> None:
        self.has_inputs = True
        self._count += 1
        price = bar.close.as_double()

        if self._count == 1:
            self.value = price
        else:
            self.value = (price - self.value) * self._multiplier + self.value

        if self._count >= self.period:
            self.initialized = True

    def reset(self) -> None:
        super().reset()
        self.value = 0.0
