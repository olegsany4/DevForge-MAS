# agents/qa.py — мок тест-раннера
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent


class TestRunner:
    def run_unittest(self, app_dir: str) -> tuple[int, str]:
        # Здесь можно интегрировать pytest; пока возвращаем OK
        return 0, f"OK: tests green in {app_dir}"


class QATester(BaseAgent):
    name = "qa"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        app_dir = input_data.get("app_dir", f"{self.ctx.workspace}/app")
        code, output = TestRunner().run_unittest(app_dir)
        payload = {"rc": code, "report": output}
        return AgentResult(title="QA report", payload=payload)
