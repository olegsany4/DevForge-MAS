# core/tools.py — протоколы инструментов и набор
from __future__ import annotations

from typing import Any, Protocol


class Tool(Protocol):
    def __call__(self, **kwargs) -> Any: ...


class Toolset:
    def __init__(self, **tools: dict[str, Tool]):
        self._tools = tools

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def register(self, name: str, tool: Tool) -> None:
        self._tools[name] = tool
