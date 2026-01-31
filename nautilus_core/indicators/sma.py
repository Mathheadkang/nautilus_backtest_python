from __future__ import annotations

from collections import deque

from nautilus_core.data import Bar
from nautilus_core.indicators.base import Indicator


class SimpleMovingAverage(Indicator):
    def __init__(self, period: int) -> None:
        super().__init__(f"SMA({period})")
        self.period = period
        self.value: float = 0.0
        self._prices: deque[float] = deque(maxlen=period)

    def handle_bar(self, bar: Bar) -> None:
        self.has_inputs = True
        self._count += 1
        price = bar.close.as_double()
        self._prices.append(price)

        self.value = sum(self._prices) / len(self._prices)

        if self._count >= self.period:
            self.initialized = True

    def reset(self) -> None:
        super().reset()
        self.value = 0.0
        self._prices.clear()
