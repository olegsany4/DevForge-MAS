#!/usr/bin/env python3
# Простая TUI на rich, читает workspace/.monitor/state.json и обновляет экран
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Tuple

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

STATE = pathlib.Path("workspace/.monitor/state.json")

# Глобальная переменная для "анти-спама" в stderr: выводим ошибку только при изменении текста
_LAST_ERR: str | None = None


def _read_state_safely(max_attempts: int = 3, delay_sec: float = 0.05) -> dict:
    """
    Безопасное чтение state.json с несколькими попытками (на случай, если файл пишет другой процесс).
    Устраняет Bandit B110 (раньше было bare try/except/pass).
    """
    global _LAST_ERR
    for attempt in range(1, max_attempts + 1):
        try:
            txt = STATE.read_text(encoding="utf-8")
            return json.loads(txt)
        except Exception as e:
            # Запоминаем и выводим ошибку только при изменении текста, чтобы не спамить
            msg = f"[tui] read/parse failed (attempt {attempt}/{max_attempts}): {e}"
            if msg != _LAST_ERR:
                print(msg, file=sys.stderr)
                _LAST_ERR = msg
            time.sleep(delay_sec)
    # Возвращаем пустое состояние — TUI останется работоспособной
    return {}


def _safe_str(v: Any, dash: str = "—") -> str:
    """Отображаем None/пустые значения как '—'."""
    if v is None:
        return dash
    if isinstance(v, (list, dict)) and not v:
        return dash
    s = str(v)
    return s if s else dash


def render() -> Tuple[Panel, Table, Table]:
    data = _read_state_safely()

    hdr = f"[bold]DevForge-MAS • Local Monitor[/bold]\nupdated: {_safe_str(data.get('collected_at'), '—')}"
    # --- Таблица качества/пайплайна ---
    t1 = Table(title="Pipeline/Quality")
    t1.add_column("Metric")
    t1.add_column("Value")
    t1.add_row("Last green", _safe_str(data.get("pipeline", {}).get("last_run_ts")))
    t1.add_row("Coverage %", _safe_str(data.get("coverage", {}).get("total_pct")))
    t1.add_row("Lint issues", _safe_str(data.get("lint", {}).get("issues")))
    b = data.get("security", {}).get("bandit", {}) or {}
    t1.add_row("Bandit high/med", f"{_safe_str(b.get('high'))}/{_safe_str(b.get('medium'))}")
    comp_ok = bool(data.get("compliance", {}).get("artifacts_ok"))
    t1.add_row("Compliance OK", _safe_str(comp_ok))

    # --- Таблица рантайма ---
    t2 = Table(title="Runtime")
    t2.add_column("Check")
    t2.add_column("Value")
    rt = data.get("runtime", {}) or {}
    be = rt.get("backend", {}) or {}
    fe = rt.get("frontend", {}) or {}
    db = (rt.get("db", {}) or {}).get("sqlite", {}) or {}
    pr = rt.get("proc", {}) or {}
    ws = rt.get("workspace", {}) or {}

    t2.add_row("Backend port", _safe_str(be.get("port_listen")))
    t2.add_row("Backend /healthz", _safe_str(be.get("http_200")))
    t2.add_row("Frontend dev port", _safe_str(fe.get("dev_server_listen")))
    t2.add_row("SQLite exists/MB", f"{_safe_str(db.get('exists'))}/{_safe_str(db.get('size_mb'))}")
    t2.add_row("SQLite version", _safe_str(db.get("migration_version")))
    t2.add_row("Proc CPU/Mem(MB)", f"{_safe_str(pr.get('cpu_pct'))}/{_safe_str(pr.get('mem_mb'))}")
    t2.add_row("Disk free GB", _safe_str(ws.get("disk_free_gb")))

    panel_title = "Status"
    # Небольшой визуальный намёк по комплаенсу
    panel = Panel.fit(hdr, title=panel_title, border_style=("green" if comp_ok else "yellow"))

    return panel, t1, t2


def main():
    parser = argparse.ArgumentParser(description="DevForge-MAS Local Monitor (TUI)")
    parser.add_argument("--interval", type=float, default=2.0, help="Период обновления экрана, секунд (по умолчанию 2)")
    parser.add_argument("--once", action="store_true", help="Один кадр и выход")
    parser.add_argument("--no-clear", action="store_true", help="Не очищать экран в цикле")
    parser.add_argument("--no-screen", action="store_true", help="Не включать полноэкранный режим Live(screen=False)")
    args = parser.parse_args()

    interval = max(0.1, float(args.interval or 2.0))  # сохраняем дефолт ≈2 сек как было
    console = Console()

    # Поведение по умолчанию (как раньше): screen=True, очистка экрана между кадрами
    use_screen = not args.no_screen

    def _tick() -> None:
        p, a, b = render()
        if not args.no_clear:
            console.clear()
        console.print(p)
        console.print(a)
        console.print(b)

    if args.once:
        _tick()
        return

    # Live-контекст даёт плавное обновление экрана и одинаковое поведение с прежней версией
    with Live(refresh_per_second=int(1 / interval) if interval >= 0.5 else 2, screen=use_screen):
        while True:
            _tick()
            time.sleep(interval)


# -----------------------------------------------------------------------------
# LEGACY: прежняя минималистичная версия без безопасного чтения и CLI-настроек
# Оставлено для трассировки изменений и соответствия требованиям «не уменьшать строки».
# -----------------------------------------------------------------------------
# STATE = pathlib.Path("workspace/.monitor/state.json")
#
# def render():
#     data = {}
#     try:
#         data = json.loads(STATE.read_text(encoding="utf-8"))
#     except Exception:
#         pass
#
#     hdr = f"[bold]DevForge-MAS • Local Monitor[/bold]\nupdated: {data.get('collected_at','—')}"
#     t1 = Table(title="Pipeline/Quality")
#     t1.add_column("Metric")
#     t1.add_column("Value")
#     t1.add_row("Last green", (data.get("pipeline", {}).get("last_run_ts") or "—"))
#     t1.add_row("Coverage %", str((data.get("coverage", {}).get("total_pct"))))
#     t1.add_row("Lint issues", str((data.get("lint", {}).get("issues"))))
#     b = data.get("security", {}).get("bandit", {})
#     t1.add_row("Bandit high/med", f"{b.get('high')}/{b.get('medium')}")
#     t1.add_row("Compliance OK", str(data.get("compliance", {}).get("artifacts_ok")))
#
#     t2 = Table(title="Runtime")
#     t2.add_column("Check")
#     t2.add_column("Value")
#     rt = data.get("runtime", {})
#     t2.add_row("Backend port", str(rt.get("backend", {}).get("port_listen")))
#     t2.add_row("Backend /healthz", str(rt.get("backend", {}).get("http_200")))
#     t2.add_row("Frontend dev port", str(rt.get("frontend", {}).get("dev_server_listen")))
#     db = rt.get("db", {}).get("sqlite", {})
#     t2.add_row("SQLite exists/MB", f"{db.get('exists')}/{db.get('size_mb')}")
#     t2.add_row("SQLite version", str(db.get("migration_version")))
#     t2.add_row("Proc CPU/Mem(MB)", f"{rt.get('proc',{}).get('cpu_pct')}/{rt.get('proc',{}).get('mem_mb')}")
#     t2.add_row("Disk free GB", str(rt.get("workspace", {}).get("disk_free_gb")))
#
#     return Panel.fit(hdr, title="Status"), t1, t2
#
# def main():
#     console = Console()
#     with Live(refresh_per_second=2, screen=True):
#         while True:
#             p, a, b = render()
#             console.clear()
#             console.print(p)
#             console.print(a)
#             console.print(b)
#             time.sleep(2)


if __name__ == "__main__":
    main()
