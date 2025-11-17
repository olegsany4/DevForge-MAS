# agents/intake_pm.py — уточнение брифа
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class IntakePM(BaseAgent):
    name = "intake_pm"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        brief: dict[str, Any] = {
            "title": input_data.get("title", "App"),
            "goal": input_data.get("goal", ""),
            "constraints": input_data.get("constraints", []),
        }
        kpi = {"tests_smoke_pass": True, "readme_ready": True}
        return AgentResult(title="Brief clarified", payload={"brief": brief, "kpi": kpi})
