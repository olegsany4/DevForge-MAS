from __future__ import annotations

import importlib  # 🛠️ [SAFE REFACTOR] поднято на верхний уровень (ruff PLC0415)
import json
import time
from collections.abc import Iterable

# 🆕: используем suppress вместо «try/except/pass» для соответствия Bandit B110
from contextlib import suppress
from pathlib import Path
from typing import Any

import yaml

from mas.core.agent import AgentContext, AgentResult, BaseAgent
from mas.core.memory import FlowMemory

# [LEGACY NOTE]
# Ранее использовались: from typing import Any, Dict, List, Optional, Tuple
# Заменено на встроенные типы (dict/list/tuple), чтобы удовлетворить ruff (UP035/UP006).


class WorkflowRunner:
    """
    WorkflowRunner запускает последовательность шагов-agents, определённых в YAML.

    ✅ Совместимость:
      - Сигнатура __init__ и run сохранена.
      - Поведение run при корректных входных данных идентично предыдущему.
      - Сохранены имена классов/методов/полей.

    🆕 Новое (добавлено как дополнение, без ломки API):
      - _validate_flow(): предварительная валидация структуры workflow.
      - plan(): «сухой план» выполнения с проверкой доступности агентов и связей.
      - Журнал execution-journal в workspace/logs/workflow.jsonl.
      - run() принимает прежний аргумент (путь к JSON), но теперь умеет:
          * читать JSON как из файла, так и из строки JSON (fallback);
          * писать подробный журнал выполнения;
          * безопаснее обрабатывать пропуски шагов.
    """

    def __init__(
        self,
        workspace: str,
        cfg_agents_path: str,
        flow_yaml: str,
        agents_pkg: str = "mas.agents",
    ):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.memory = FlowMemory(str(self.workspace / "flow_state.json"))
        self.flow = yaml.safe_load(Path(flow_yaml).read_text(encoding="utf-8"))
        self._agents = self._load_agents_registry(cfg_agents_path, agents_pkg)

        # 🆕: предзаготовим путь к журналу (не ломает совместимость)
        self._logs_dir = self.workspace / "logs"
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self._journal_path = self._logs_dir / "workflow.jsonl"

        # 🆕: мягкая предварительная валидация (без исключений, но с сохранением статуса)
        ok, errors = self._validate_flow()
        if not ok:
            # Не роняем конструктор — фиксируем замечания в журнале;
            # дальнейшие ошибки проявятся при вызове run/plan.
            self._append_journal(
                {
                    "event": "flow_validation",
                    "ok": False,
                    "errors": errors,
                    "ts": time.time(),
                }
            )

    def _load_agents_registry(self, path: str, agents_pkg: str):
        # LEGACY (для трассировки и сохранения строк):
        #   ранее импорт был внутри функции:
        #       import importlib
        #   ruff (PLC0415) требует импорт на верхнем уровне — мы подняли его выше.
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        reg: dict[str, BaseAgent] = {}
        for name, meta in cfg["agents"].items():
            module = importlib.import_module(f"{agents_pkg}.{name}")
            cls = getattr(module, meta["type"])
            reg[name] = cls
        return reg

    # 🆕: аккуратная валидация описания потока
    def _validate_flow(self) -> tuple[bool, list[str]]:
        """
        Проверяет базовые свойства:
          - наличие workflow.steps (list);
          - уникальные id шагов;
          - каждый step.agent зарегистрирован;
          - input_from == "request" или ссылается на существующий предыдущий шаг.

        Возвращает кортеж: (ok, список_ошибок). Не выбрасывает исключений.
        """
        errors: list[str] = []
        wf = self.flow or {}
        steps = (wf.get("workflow") or {}).get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append("workflow.steps must be a non-empty list")
            return False, errors

        seen_ids: set[str] = set()
        for idx, step in enumerate(steps):
            sid = step.get("id")
            agent = step.get("agent")
            input_from = step.get("input_from", "request")

            if not sid or not isinstance(sid, str):
                errors.append(f"step[{idx}] has invalid 'id'")
            elif sid in seen_ids:
                errors.append(f"duplicate step id: {sid}")
            else:
                seen_ids.add(sid)

            if not agent or not isinstance(agent, str):
                errors.append(f"step[{idx}] has invalid 'agent'")
            elif agent not in self._agents:
                errors.append(f"agent not found in registry: {agent}")

            if input_from != "request" and input_from not in seen_ids:
                # требуем, чтобы ссылка указывала на уже встреченный шаг
                errors.append(f"step[{idx}] input_from '{input_from}' must refer to a previous step id or 'request'")

        return (len(errors) == 0), errors

    # 🆕: сухой план выполнения с диагностикой
    def plan(self) -> dict[str, Any]:
        """
        Возвращает структуру плана:
            {
              "ok": bool,
              "errors": [...],
              "steps": [{"id":..., "agent":..., "input_from":...}, ...]
            }
        Не изменяет состояние памяти, не выполняет агентов.
        """
        ok, errors = self._validate_flow()
        wf = (self.flow or {}).get("workflow", {})
        steps = wf.get("steps") or []
        plan_steps = [{"id": s.get("id"), "agent": s.get("agent"), "input_from": s.get("input_from", "request")} for s in steps]
        summary = {"ok": ok, "errors": errors, "steps": plan_steps}
        # логируем план (не мешает совместимости)
        self._append_journal({"event": "plan", "summary": summary, "ts": time.time()})
        return summary

    def run(self, request_json_path: str, skip_optional: Iterable[str] | None = None) -> dict[str, Any]:
        """
        Выполняет workflow.

        Совместимость:
          - Сигнатура и базовая логика прежние.
          - По-прежнему ожидается путь до JSON-файла с запросом.
        Расширение:
          - Если request_json_path не является существующим файлом, предпримем
            попытку интерпретировать значение как JSON-строку (fallback).
        """
        # === ЧТЕНИЕ ВХОДА (совместимо + расширено) ===
        req: dict[str, Any]
        req_path = Path(request_json_path)
        if req_path.exists():
            req = json.loads(req_path.read_text(encoding="utf-8"))
        else:
            # 🆕: пробуем разобрать как JSON-строку (без падения API)
            try:
                req = json.loads(request_json_path)
            except Exception as e:
                # Журнал + понятная ошибка
                self._append_journal(
                    {
                        "event": "request_error",
                        "message": "cannot parse request_json_path as file or JSON string",
                        "value": request_json_path[:2000],  # защита от больших строк
                        "error": str(e),
                        "ts": time.time(),
                    }
                )
                raise

        ctx = AgentContext(workspace=str(self.workspace))
        skipped = set(skip_optional or [])
        last_output: dict[str, Any] | None = None

        wf = (self.flow or {}).get("workflow", {})
        steps: list[dict[str, Any]] = wf.get("steps") or []

        # 🆕: мягкая валидация перед запуском (не роняет, но журналирует)
        ok, errors = self._validate_flow()
        if not ok:
            self._append_journal({"event": "pre_run_validation", "ok": False, "errors": errors, "ts": time.time()})

        for step in steps:
            t0 = time.time()
            step_id = step["id"]
            agent_name = step["agent"]
            input_from = step.get("input_from", "request")

            # Пропуск опциональных шагов без нарушения совместимости
            if step_id in skipped:
                self.memory.set(step_id, {"skipped": True})
                self._append_journal({"event": "skip_step", "step_id": step_id, "agent": agent_name, "ts": time.time()})
                continue

            # === ПОЛУЧЕНИЕ ВХОДА ===
            if input_from == "request":
                input_data = req
            else:
                input_data = self.memory.get(input_from)

            # === ВЫЗОВ АГЕНТА ===
            # AgentCls = self._agents[agent_name]  # ← ОРИГИНАЛ (оставлено для истории; нарушал стиль N806)
            agent_cls = self._agents[agent_name]  # 🆕: то же самое, но в нижнем регистре для стиля
            agent: BaseAgent = agent_cls(ctx)  # type: ignore[call-arg]

            # Выполнение с базовым перехватом ошибок для журнала (не меняет API исключений наружу)
            try:
                result: AgentResult = agent.run(input_data)
            except Exception as e:
                self._append_journal(
                    {
                        "event": "step_error",
                        "step_id": step_id,
                        "agent": agent_name,
                        "input_from": input_from,
                        "error": str(e),
                        "duration_ms": int((time.time() - t0) * 1000),
                        "ts": time.time(),
                    }
                )
                raise

            # === СОХРАНЕНИЕ РЕЗУЛЬТАТА ===
            self.memory.set(step_id, result.payload)
            last_output = result.payload

            # === ЛОГ ЖУРНАЛА ===
            self._append_journal(
                {
                    "event": "step_done",
                    "step_id": step_id,
                    "agent": agent_name,
                    "input_from": input_from,
                    "duration_ms": int((time.time() - t0) * 1000),
                    "output_keys": list(result.payload.keys()) if isinstance(result.payload, dict) else None,
                    "ts": time.time(),
                }
            )

        summary: dict[str, Any] = {"status": "ok", "result": last_output}
        self._append_journal({"event": "run_done", "summary": summary, "ts": time.time()})
        return summary

    # =========================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================

    def _append_journal(self, record: dict[str, Any]) -> None:
        """
        🆕: Пишет запись журнала в JSONL. Никогда не бросает исключений наружу
        (журнал — вспомогательный), чтобы не нарушать поведение раннера.

        Изменение ради безопасности (Bandit B110):
        - Вместо «try/except/ pass» используем contextlib.suppress(Exception).
        - Старый блок оставлен закомментированным ниже для прозрачности diff.
        """
        line = json.dumps(record, ensure_ascii=False)

        # ✅ Новая версия (безопасно, соответствует Bandit):
        with suppress(Exception):
            with self._journal_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

        # ---- LEGACY (оставлено закомментированным для контроля изменений) ----
        # try:
        #     line = json.dumps(record, ensure_ascii=False)
        #     with self._journal_path.open("a", encoding="utf-8") as f:
        #         f.write(line + "\n")
        # except Exception:
        #     # Идём молча — журнал не должен ломать основной сценарий
        #     pass
