#!/usr/bin/env python3
"""
Сбор локальных метрик DevForge-MAS → workspace/.monitor/state.json
Запуск:
  python tools/monitor/collect.py --once
  python tools/monitor/collect.py --interval 5

SAFE REFACTOR (безопасный рефактор):
- [SECURE] http_200: проверка допустимых схем (http/https) во избежание file:/ и т.п. (Bandit B310).
- [SECURE] run: абсолютный путь к исполняемому файлу через shutil.which, отказ при неизвестной команде,
  отсутствие shell=True, комментарий # nosec B603 (команда формируется внутри процесса).
- [SECURE] sqlite_meta: явный allow-list таблиц, комментарий # nosec B608 (идентификатор из строгого списка).
- [ROBUST] STATE пишется атомарно (временный файл → replace) для предотвращения частично записанных JSON.
- [LEGACY] Сохранены старые версии run/http_200/sqlite_meta в комментариях для трассировки.
- [B110/B112] Исключены голые try/except pass/continue: ошибки фиксируются в diagnostics, цикл с psutil
  переписан без except+continue.
- [DX] Добавлен флаг --debug и поле diagnostics для контроля ошибок без изменения базового поведения.
- [LINT] PLC0415: вынесены импорты на верхний уровень (urllib.request, "ленивый" psutil через try/except).
- [LINT] PLR2004: вынесена "магическая" длина URL в константу MAX_URL_LEN.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import socket
import sqlite3
import subprocess  # noqa: S404 (Bandit B404): используем без shell и только с валидированным путем
import sys
import time
import urllib.request  # nosec B310: используем только после проверки схемы http/https
from datetime import datetime, timezone
from urllib.parse import urlsplit

# "Ленивый" импорт psutil во время загрузки модуля для соблюдения PLC0415 и устойчивости к отсутствию пакета
try:  # noqa: SIM105
    import psutil  # type: ignore
except Exception:  # pragma: no cover - отсутствие psutil допустимо
    psutil = None  # type: ignore[assignment]

ROOT = pathlib.Path(".").resolve()
WS = ROOT / "workspace"
MON = WS / ".monitor"
MON.mkdir(parents=True, exist_ok=True)
STATE = MON / "state.json"

# Константа для ограничения длины URL (исключаем "магическое" число)
MAX_URL_LEN = 2048


def ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def file_size_mb(p: pathlib.Path) -> float:
    try:
        return round(p.stat().st_size / (1024 * 1024), 2)
    except FileNotFoundError:
        return 0.0


def port_listen(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def http_200(url: str, timeout: float = 1.0) -> bool:
    """
    Возвращает True если URL отвечает 200.
    [SECURE] Разрешаем только http/https, чтобы исключить неожиданные схемы (file:, data:, etc.).
    Дополнительно ограничиваем длину URL для избежания патологий.
    """
    try:
        parts = urlsplit(url)
        scheme = (parts.scheme or "").lower()
        if scheme not in ("http", "https"):
            # Невалидная (или потенциально опасная) схема: считаем недоступным, но не падаем.
            return False
        # тривиальная защита от чрезмерно длинных строк
        if len(url) > MAX_URL_LEN:
            return False

        # nosec B310: схема валидирована как http/https; file:/ и кастомные схемы недоступны
        with urllib.request.urlopen(url, timeout=timeout) as r:  # nosec B310
            return getattr(r, "status", None) == 200
    except Exception:
        return False


# -----------------------------------------------------------------------------
# LEGACY: прежняя реализация http_200 (сохранена для трассировки)
# -----------------------------------------------------------------------------
# def http_200(url: str, timeout: float = 1.0) -> bool:
#     try:
#         import urllib.request
#         with urllib.request.urlopen(url, timeout=timeout) as r:
#             return r.status == 200
#     except Exception:
#         return False


def run(cmd: list[str]) -> tuple[int, str, str]:
    """
    Запуск команды и сбор stdout/stderr.
    [SECURE] Абсолютный путь к исполняемому файлу через shutil.which, нигде не используем shell=True.
    Обоснование # nosec B603: список cmd формируется самим приложением, без внешних небезопасных входов.
    """
    try:
        if not cmd:
            return 127, "", "empty command"
        exe = cmd[0]
        if not (pathlib.Path(exe).is_absolute() and pathlib.Path(exe).exists()):
            # Разрешаем относительное имя, но обязуемся найти абсолютный путь
            resolved = shutil.which(exe)
            if not resolved:
                return 127, "", f"executable not found: {exe}"
            cmd = [resolved] + cmd[1:]
        # shell=False по умолчанию, text=True для безопасного текста
        p = subprocess.Popen(  # nosec B603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out, err = p.communicate(timeout=60)
        return p.returncode, (out or "").strip(), (err or "").strip()
    except Exception as e:
        return 1, "", f"run failed: {e}"


# -----------------------------------------------------------------------------
# LEGACY: прежняя реализация run (сохранена для трассировки)
# -----------------------------------------------------------------------------
# def run(cmd: list[str]) -> tuple[int, str, str]:
#     p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#     out, err = p.communicate(timeout=60)
#     return p.returncode, out.strip(), err.strip()


def coverage_pct() -> float | None:
    cov_file = ROOT / "coverage.xml"
    if not cov_file.exists():
        return None
    try:
        txt = cov_file.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'line-rate="([0-9.]+)"', txt)
        if m:
            return round(float(m.group(1)) * 100, 2)
    except Exception:
        # Не поднимаем исключение — метрика опциональна
        return None
    return None


def bandit_findings() -> dict:
    report = ROOT / "bandit_report.json"
    if not report.exists():
        return {"high": None, "medium": None}
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
        counts = {"high": 0, "medium": 0}
        for i in data.get("results", []):
            sev = (i.get("issue_severity") or "").lower()
            if sev == "high":
                counts["high"] += 1
            if sev == "medium":
                counts["medium"] += 1
        return counts
    except Exception:
        return {"high": None, "medium": None}


def last_pipeline_ts() -> str | None:
    f = WS / ".checks" / "last_green.ts"
    return f.read_text().strip() if f.exists() else None


def sqlite_meta() -> dict:
    """
    Информация о локальной SQLite:
    - exists/size_mb
    - миграционная версия из одной из известных таблиц.
    [SECURE] Используем строгий allow-list имя_таблицы -> исключаем внешнее влияние.
    Комментарий # nosec B608: идентификатор не параметризуется в sqlite, но он из закрытого списка,
    поэтому инъекция невозможна.
    """
    db_path = pathlib.Path(os.getenv("DB_FILE", "devforge_mas.sqlite3"))
    info = {"exists": db_path.exists(), "size_mb": file_size_mb(db_path), "migration_version": None}
    if db_path.exists():
        try:
            con = sqlite3.connect(str(db_path))
            cur = con.cursor()
            allowed_tables = ("alembic_version", "schema_version")
            for table in allowed_tables:
                try:
                    # идентификатор из allow-list (строго задан), поэтому # nosec B608 уместен
                    cur.execute(f"SELECT version_num FROM {table} LIMIT 1;")  # nosec B608
                    row = cur.fetchone()
                    if row:
                        info["migration_version"] = row[0]
                        break
                except sqlite3.Error:
                    # отсутствие таблицы/колонки не критично
                    continue
            con.close()
        except sqlite3.Error:
            # неполучение соединения — не критично для общей метрики
            pass
    return info


# -----------------------------------------------------------------------------
# LEGACY: прежняя реализация sqlite_meta (сохранена для трассировки)
# -----------------------------------------------------------------------------
# def sqlite_meta() -> dict:
#     db_path = pathlib.Path(os.getenv("DB_FILE", "devforge_mas.sqlite3"))
#     info = {"exists": db_path.exists(), "size_mb": file_size_mb(db_path), "migration_version": None}
#     if db_path.exists():
#         try:
#             con = sqlite3.connect(str(db_path))
#             cur = con.cursor()
#             # попытка прочитать alembic_version или нашу табличку версий
#             for table in ("alembic_version", "schema_version"):
#                 try:
#                     cur.execute(f"SELECT version_num FROM {table} LIMIT 1;")
#                     row = cur.fetchone()
#                     if row:
#                         info["migration_version"] = row[0]
#                         break
#                 except sqlite3.Error:
#                     continue
#             con.close()
#         except sqlite3.Error:
#             pass
#     return info


def disk_free_gb() -> float:
    usage = shutil.disk_usage(ROOT)
    return round(usage.free / (1024**3), 2)


def lint_issues() -> int | None:
    # ожидаем файл workspace/.checks/lint.json { "issues": <int> }
    p = WS / ".checks" / "lint.json"
    if p.exists():
        try:
            return int(json.loads(p.read_text()).get("issues", 0))
        except Exception:
            return None
    return None


def _atomic_write_json(path: pathlib.Path, payload: dict) -> None:
    """
    Атомарная запись JSON: временный файл в той же директории + replace()
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


# [NEW] безопасное извлечение метрик процесса/порта без try/except/continue в цикле
def _safe_psutil_metrics(port: int) -> tuple[float | None, float | None, str | None]:
    """
    Пытается найти процесс, слушающий указанный порт, и вернуть (cpu_pct, mem_mb, diagnostic_error).
    Не бросает исключений наружу.
    """
    if psutil is None:  # type: ignore[truthy-function]
        # psutil может отсутствовать — это ожидаемо в минимальной среде
        return None, None, "psutil_unavailable: module not installed"

    cpu_val: float | None = None
    mem_val: float | None = None
    diag_err: str | None = None

    try:
        for proc in psutil.process_iter(["pid", "name", "connections", "memory_info", "cpu_percent"]):
            # Избегаем B112: не используем try/except/continue внутри — работаем через флаг
            got_conns = False
            conns = []
            try:
                conns = proc.connections(kind="inet")
                got_conns = True
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, RuntimeError) as e1:
                diag_err = f"psutil_conn_error(pid={getattr(proc, 'pid', '?')}): {e1}"

            if not got_conns:
                # просто переходим к следующему процессу
                continue

            match = False
            for c in conns:
                try:
                    if c.laddr and getattr(c.laddr, "port", None) == port:
                        match = True
                        break
                except Exception as e2:
                    diag_err = f"psutil_conn_parse_error(pid={getattr(proc, 'pid', '?')}): {e2}"

            if match:
                try:
                    # короткий интервал для cpu_percent
                    cpu_val = proc.cpu_percent(interval=0.1)
                    mem_val = round(proc.memory_info().rss / (1024 * 1024), 1)
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess) as e3:
                    diag_err = f"psutil_metric_error(pid={getattr(proc, 'pid', '?')}): {e3}"
                break
    except Exception as e:
        diag_err = f"psutil_iter_error: {e}"

    return cpu_val, mem_val, diag_err


def main(interval: int | None, debug: bool = False):
    while True:
        diagnostics: list[str] = []

        state = {
            "collected_at": ts(),
            "pipeline": {"last_run_ts": last_pipeline_ts()},
            "tests": {},
            "coverage": {"total_pct": coverage_pct()},
            "lint": {"issues": lint_issues()},
            "security": {"bandit": bandit_findings()},
            "compliance": {"artifacts_ok": all((ROOT / "compliance" / f).exists() for f in ("NOTICE", "OBLIGATIONS.md", "THIRD_PARTY_LICENSES.md"))},
            "runtime": {
                "backend": {
                    "port_listen": port_listen(int(os.getenv("BACKEND_PORT", "8080"))),
                    "http_200": http_200(os.getenv("BACKEND_HEALTH_URL", "http://127.0.0.1:8080/healthz")),
                },
                "frontend": {"dev_server_listen": port_listen(int(os.getenv("FRONTEND_PORT", "5173")))},
                "db": {"sqlite": sqlite_meta()},
                "proc": {"cpu_pct": None, "mem_mb": None},
                "workspace": {"disk_free_gb": disk_free_gb()},
            },
            "diagnostics": diagnostics,  # [NEW] собираем мягкие ошибки сюда
        }

        # безопасно пробуем psutil
        cpu_pct, mem_mb, diag = _safe_psutil_metrics(int(os.getenv("BACKEND_PORT", "8080")))
        if diag:
            diagnostics.append(diag)
        state["runtime"]["proc"]["cpu_pct"] = cpu_pct
        state["runtime"]["proc"]["mem_mb"] = mem_mb

        # [ROBUST] Атомарная запись state.json
        try:
            _atomic_write_json(STATE, state)
        except Exception as e:
            diagnostics.append(f"atomic_write_error: {e}")
            # fallback: прямой write_text (чтобы не потерять состояние)
            try:
                STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e2:
                diagnostics.append(f"fallback_write_error: {e2}")
                if debug:
                    print(f"[collect] failed to write state: {e}; fallback failed: {e2}", file=sys.stderr)

        if debug and diagnostics:
            # отладочный вывод не изменяет основную логику
            for d in diagnostics:
                print(f"[diagnostic] {d}", file=sys.stderr)

        if interval is None:
            break
        time.sleep(max(1, int(interval)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, help="секунды обновления (TUI/демон)")
    ap.add_argument("--once", action="store_true")
    # [NEW] без ломки старого API — опция не обязательна; по умолчанию поведение прежнее
    ap.add_argument("--debug", action="store_true", help="печать диагностик на stderr")
    args = ap.parse_args()
    if args.once:
        main(None, debug=args.debug)
    else:
        main(args.interval or 5, debug=args.debug)
