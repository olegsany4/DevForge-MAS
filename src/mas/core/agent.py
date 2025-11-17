# core/agent.py — минимальная, но полная реализация базовых сущностей
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AgentContext(BaseModel):
    workspace: str
    memory: dict[str, Any] = {}  # простая in-memory мапа; файловая память в FlowMemory


class AgentResult(BaseModel):
    title: str
    payload: dict[str, Any]


class BaseAgent:
    name: str = "base"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def run(self, input_data: dict[str, Any]) -> AgentResult:  # pragma: no cover
        raise NotImplementedError


# NOTE: ничего не меняли по API; только сделали валидный код и оставили точку расширения.
