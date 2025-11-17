# core/bus.py — простой синхронный EventBus
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class EventBus:
    def __init__(self):
        self._subs: dict[str, list[Callable[[Any], None]]] = {}

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        self._subs.setdefault(topic, []).append(handler)

    def publish(self, topic: str, event: Any) -> None:
        for h in self._subs.get(topic, []):
            h(event)
