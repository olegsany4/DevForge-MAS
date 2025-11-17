# agents/researcher.py — исследователь (моки фактов)
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class Researcher(BaseAgent):
    name = "researcher"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        # Мок фактоидами; затем подключим web/RAG инструменты
        payload: dict[str, Any] = {
            "assumptions": ["MVP scope", "Public stack"],
            "references": [],  # сюда добавим источники
            "risks": ["Timebox tight"],
            "mitigations": ["WBS with timebox"],
        }
        return AgentResult(title="FactSheet", payload=payload)
