# agents/ux_writer.py — UX микрокопи
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class UXWriter(BaseAgent):
    name = "ux_writer"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        return AgentResult(
            title="UX microcopy",
            payload={"strings": {"ok": "OK", "cancel": "Cancel"}},
        )
