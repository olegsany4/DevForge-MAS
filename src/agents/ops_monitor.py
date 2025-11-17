# agents/ops_monitor.py — наблюдаемость
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class OpsMonitor(BaseAgent):
    name = "ops_monitor"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        payload: dict[str, Any] = {"metrics": ["http_requests_total"], "alerts": ["service_down"]}
        return AgentResult(title="Observability preset", payload=payload)
