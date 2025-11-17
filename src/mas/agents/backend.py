# agents/backend.py — рабочий мок генерации бэкенда
from __future__ import annotations

from typing import Any

from mas.core.agent import AgentResult, BaseAgent
from mas.tools.codegen import SimpleCodeGen
from mas.tools.repo import RepoOps


class BackendDev(BaseAgent):
    name = "backend"

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        app_dir = f"{self.ctx.workspace}/app"
        repo = RepoOps(app_dir)
        repo.ensure_gitkeep(".")
        code = SimpleCodeGen().generate_flask_todo()
        for path, content in code.items():
            repo.write_file(path, content)
        payload = {"app_dir": app_dir, "files": list(code.keys())}
        return AgentResult(title="Backend generated", payload=payload)
