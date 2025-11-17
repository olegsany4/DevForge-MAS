from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class Compliance(BaseAgent):
    name = "compliance"


def run(self, input_data: dict[str, Any]) -> AgentResult:
    payload = {"licenses": ["MIT"], "notice": True, "privacy": "N/A for MVP"}
    return AgentResult(title="Compliance report", payload=payload)
