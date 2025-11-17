# agents/techlead.py — техбаза (совместимо с ранее оговорённым toolchain)
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class TechLead(BaseAgent):
    name = "techlead"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        payload: dict[str, Any] = {
            "toolchain": {"python": ">=3.11", "pkg": ["ruff", "pytest"]},
            "linters": {"ruff": {"select": ["E", "F", "I"]}},
            "branch_policy": {"main": "protected", "feat/*": "PR required"},
        }
        return AgentResult(title="Tech baseline", payload=payload)
