from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class TimeEvent:
    name: str
    ts_event: int
    ts_init: int
    callback: Callable | None = None

    def __repr__(self) -> str:
        return f"TimeEvent('{self.name}', ts={self.ts_event})"


@dataclass
class Timer:
    name: str
    callback: Callable
    interval_ns: int
    start_time_ns: int
    next_time_ns: int
    stop_time_ns: int | None = None


class Clock:
    def __init__(self) -> None:
        self._timers: dict[str, Timer] = {}

    @property
    def timestamp_ns(self) -> int:
        raise NotImplementedError

    @property
    def timestamp_ms(self) -> int:
        return self.timestamp_ns // 1_000_000

    def set_timer(
        self,
        name: str,
        interval_ns: int,
        callback: Callable,
        start_time_ns: int | None = None,
        stop_time_ns: int | None = None,
    ) -> None:
        start = start_time_ns or self.timestamp_ns
        self._timers[name] = Timer(
            name=name,
            callback=callback,
            interval_ns=interval_ns,
            start_time_ns=start,
            next_time_ns=start + interval_ns,
            stop_time_ns=stop_time_ns,
        )

    def cancel_timer(self, name: str) -> None:
        self._timers.pop(name, None)

    @property
    def timer_names(self) -> list[str]:
        return list(self._timers.keys())

    @property
    def timer_count(self) -> int:
        return len(self._timers)


class TestClock(Clock):
    def __init__(self, initial_ns: int = 0) -> None:
        super().__init__()
        self._time_ns = initial_ns

    @property
    def timestamp_ns(self) -> int:
        return self._time_ns

    def set_time(self, time_ns: int) -> None:
        self._time_ns = time_ns

    def advance_time(self, to_time_ns: int) -> list[TimeEvent]:
        events: list[TimeEvent] = []
        expired: list[str] = []

        for name, timer in self._timers.items():
            while timer.next_time_ns <= to_time_ns:
                if timer.stop_time_ns is not None and timer.next_time_ns > timer.stop_time_ns:
                    expired.append(name)
                    break
                event = TimeEvent(
                    name=timer.name,
                    ts_event=timer.next_time_ns,
                    ts_init=timer.next_time_ns,
                    callback=timer.callback,
                )
                events.append(event)
                timer.next_time_ns += timer.interval_ns

        for name in expired:
            self._timers.pop(name, None)

        self._time_ns = to_time_ns
        events.sort(key=lambda e: e.ts_event)
        return events


class LiveClock(Clock):
    @property
    def timestamp_ns(self) -> int:
        return int(time.time() * 1_000_000_000)
