# agents/security.py — базовая ИБ
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class Security(BaseAgent):
    name = "security"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        payload: dict[str, Any] = {
            "threats": ["Injection", "Secrets leak"],
            "checks": ["sast", "secret-scan"],
            "hardening": [".env.example only", "dependencies pin"],
        }
        return AgentResult(title="Security baseline", payload=payload)
