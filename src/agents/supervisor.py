# agents/supervisor.py — маршрутизация шагов (мок)
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class Supervisor(BaseAgent):
    name = "supervisor"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        # На MVP этапе просто ретранслируем brief и включаем все шаги.
        # В дальнейшем: выбор веток/остановок по KPI.
        payload: dict[str, Any] = {
            "route": ("intake→research→plan→design→techbase→be→fe→data→sec→qa→docs→review→compliance→integrate→release→observe"),
            "policy": {"quality_over_speed": True},
        }
        return AgentResult(title="Supervisor plan", payload=payload)
