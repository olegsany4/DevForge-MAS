# agents/reviewer.py — код-ревью (мок)
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class Reviewer(BaseAgent):
    name = "reviewer"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        payload: dict[str, Any] = {"verdict": "approve", "notes": ["MVP acceptable"]}
        return AgentResult(title="Code review", payload=payload)
