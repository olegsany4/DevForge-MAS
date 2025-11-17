# agents/planner.py — план работ
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class Planner(BaseAgent):
    name = "planner"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        title = input_data.get("title", "App")
        goal = input_data.get("goal", "")
        acceptance: list[str] = list(input_data.get("acceptance", []))
        tasks = [
            "intake",
            "research",
            "design",
            "backend",
            "frontend",
            "docs",
            "qa",
            "release",
        ]
        payload = {"title": title, "goal": goal, "acceptance": acceptance, "tasks": tasks}
        return AgentResult(title=f"Plan for {title}", payload=payload)
