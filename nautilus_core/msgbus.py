from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class MessageBus:
    def __init__(self, trader_id: str | None = None) -> None:
        self.trader_id = trader_id
        self._subscriptions: dict[str, list[Callable]] = defaultdict(list)
        self._endpoints: dict[str, Callable] = {}

    def subscribe(self, topic: str, handler: Callable) -> None:
        if handler not in self._subscriptions[topic]:
            self._subscriptions[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable) -> None:
        subs = self._subscriptions.get(topic, [])
        if handler in subs:
            subs.remove(handler)

    def publish(self, topic: str, msg: Any) -> None:
        for handler in self._subscriptions.get(topic, []):
            handler(msg)

    def register(self, endpoint: str, handler: Callable) -> None:
        self._endpoints[endpoint] = handler

    def deregister(self, endpoint: str) -> None:
        self._endpoints.pop(endpoint, None)

    def send(self, endpoint: str, msg: Any) -> None:
        handler = self._endpoints.get(endpoint)
        if handler is not None:
            handler(msg)

    def has_subscribers(self, topic: str) -> bool:
        return bool(self._subscriptions.get(topic))

    def subscriptions(self, topic: str) -> list[Callable]:
        return list(self._subscriptions.get(topic, []))

    @property
    def topics(self) -> list[str]:
        return [t for t, subs in self._subscriptions.items() if subs]

    @property
    def endpoints(self) -> list[str]:
        return list(self._endpoints.keys())
