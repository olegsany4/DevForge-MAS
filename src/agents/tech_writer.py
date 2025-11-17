# agents/tech_writer.py — документация
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class TechWriter(BaseAgent):
    name = "tech_writer"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        payload: dict[str, Any] = {"docs": ["README.md", "ADR.md", "API.md"]}
        return AgentResult(title="Docs scaffold", payload=payload)
