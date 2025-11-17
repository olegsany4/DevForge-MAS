# agents/integrator.py — сборка summary из ранее полученных данных
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent
from mas.tools.doc_builder import DocBuilder
from mas.tools.repo import RepoOps


class Integrator(BaseAgent):
    name = "integrator"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        app_dir = f"{self.ctx.workspace}/app"
        repo = RepoOps(app_dir)
        plan = input_data.get("plan", {"title": input_data.get("title", "App")})
        design = input_data.get("design", {"modules": ["api", "backend"]})
        summary = DocBuilder().build_summary(plan, design)
        repo.write_file("SUMMARY.md", summary)
        return AgentResult(title="Integrated", payload={"summary_path": f"{app_dir}/SUMMARY.md"})
