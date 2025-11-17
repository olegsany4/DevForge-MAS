# agents/architect.py — фикс аннотаций, удаление неиспользуемой переменной
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class Architect(BaseAgent):
    name = "architect"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        tech: dict[str, Any] = input_data.get("tech", {})
        modules = ["api", "backend", "frontend", "docs"]
        payload = {
            "title": input_data.get("title", "App"),
            "tech": tech,
            "modules": modules,
            "ci": {"jobs": ["lint", "test"]},
        }
        return AgentResult(title=f"Design for {payload['title']}", payload=payload)
