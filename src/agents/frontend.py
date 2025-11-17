# agents/frontend.py — мок фронтенда
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class FrontendDev(BaseAgent):
    name = "frontend"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        payload = {
            "files": ["frontend/README.md", "frontend/package.json"],
            "note": "FE optional in MVP",
        }
        return AgentResult(title="Frontend scaffold", payload=payload)
