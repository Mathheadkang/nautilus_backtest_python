from __future__ import annotations

from nautilus_core.data import Bar


class Indicator:
    def __init__(self, name: str) -> None:
        self.name = name
        self.initialized = False
        self.has_inputs = False
        self._count = 0

    def handle_bar(self, bar: Bar) -> None:
        raise NotImplementedError

    def reset(self) -> None:
        self.initialized = False
        self.has_inputs = False
        self._count = 0

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name})"
