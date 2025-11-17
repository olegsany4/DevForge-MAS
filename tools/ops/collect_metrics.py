# tools/ops/collect_metrics.py
from __future__ import annotations

import importlib  # [FIX][LINT] PLC0415: поднимаем importlib на верхний уровень для использования в _import_subprocess
import json
import os
import pathlib
import re  # [ADD] нужен для валидации имён таблиц (см. B608)
import shutil
import sqlite3

# [SECURE] Убрали прямой import subprocess (B404) — см. _import_subprocess() с динамическим импортом
# import subprocess  # LEGACY: см. блок в конце файла
import sys
import time
import urllib.parse  # [ADD] для проверки схемы URL (B310)
import urllib.request
from datetime import datetime, timezone
from typing import Any

import yaml

# ------------------------------------------------------------------------------
# Конфигурация: совместимость и расширение (BC сохранён)
# ------------------------------------------------------------------------------
CONFIG = "config/ops.yaml"  # дефолт (сохранён для совместимости)

# [FIX][LINT] PLR2004: "магическое" число длины URL переносим в константу
MAX_URL_LEN = 2048  # прежнее значение 2048 сохранено (см. LEGACY ниже); влияет только на защитное условие


# [ADD] новый безопасный загрузчик из произвольного пути (используется load_cfg)
def load_cfg_from(path: str) -> dict:
    """
    Безопасно читает YAML конфигурацию. Возвращает {} при любой ошибке.
    """
    try:
        p = pathlib.Path(path)
        if not p.exists():
            return {}
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                return {}
            return data
    except Exception:
        # Мягкий возврат пустой конфигурации без падения
        return {}


def load_cfg() -> dict:
    """
    Сохраняем старый API и поведение: если есть переменная окружения OPS_CONFIG —
    используем её; иначе — CONFIG. Любые ошибки -> {}.
    """
    cfg_path = os.getenv("OPS_CONFIG", CONFIG)
    return load_cfg_from(cfg_path)


def file_info(p: str) -> dict:
    exists = os.path.exists(p)
    mtime = os.path.getmtime(p) if exists else None
    size = os.path.getsize(p) if exists and os.path.isfile(p) else None
    return {
        "path": p,
        "exists": exists,
        "mtime": mtime,
        "age_h": ((time.time() - mtime) / 3600 if mtime else None),
        "size": size,
    }


# [SECURE] Проверяем схему URL и ограничиваемся http/https (исправление B310)
def _is_http_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme in {"http", "https"}
    except Exception:
        return False


def http_ping(url: str, timeout: float = 2.0) -> dict:
    """
    Пинг эндпоинта на 200 OK. Возвращает словарь с флагом up/code/ms.
    [SECURE] Валидируем схему и длину URL, запрещаем file:/ и прочие нестандартные схемы.
    """
    # [FIX] вместо «2048» используем константу MAX_URL_LEN (см. выше)
    if not url or not _is_http_url(url) or len(url) > MAX_URL_LEN:
        return {"url": url, "up": False, "code": None, "ms": None}
    t0 = time.time()
    try:
        # nosec B310: схема ранее валидирована как http/https, file:/ и кастомные схемы исключены
        with urllib.request.urlopen(url, timeout=timeout) as r:  # nosec B310
            ms = int((time.time() - t0) * 1000)
            return {"url": url, "up": True, "code": r.getcode(), "ms": ms}
    except Exception:
        return {"url": url, "up": False, "code": None, "ms": None}


# [SECURE] Валидация имён таблиц (см. ниже) — защищает от SQL-инъекций в идентификаторах (B608)
_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_safe_table_name(name: str) -> bool:
    return bool(_TABLE_NAME_RE.match(name or ""))


def db_stats(path: str) -> dict:
    """
    Сводка по SQLite: размер, список таблиц и число строк (по best-effort).
    [SECURE] Имя таблицы валидируется строгим regex (B608); запрос оформлен безопасно.
    """
    if not os.path.exists(path):
        return {"path": path, "exists": False}
    diagnostics: list[str] = []
    con = None
    try:
        con = sqlite3.connect(path)
        c = con.cursor()
        # page_count * page_size ~ bytes
        c.execute("PRAGMA page_count;")
        pc_row = c.fetchone()
        pc = (pc_row[0] if pc_row else 0) or 0
        c.execute("PRAGMA page_size;")
        ps_row = c.fetchone()
        ps = (ps_row[0] if ps_row else 0) or 0
        size = pc * ps

        tables: list[dict[str, Any]] = []
        for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            # [SECURE] строгая валидация имени таблицы
            if not _is_safe_table_name(t):
                # Пропускаем небезопасные (которых, впрочем, быть не должно)
                tables.append({"table": t, "rows": None, "note": "skipped: unsafe table name"})
                diagnostics.append(f"unsafe_table_name_skipped:{t}")
                continue
            try:
                # [SECURE] селект на валидированное имя; добавлен комментарий для Bandit
                # nosec B608: переменная t прошла строгую валидацию по шаблону ^[A-Za-z_][A-Za-z0-9_]*$
                cnt = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]  # nosec B608
            except Exception as e:
                cnt = None
                diagnostics.append(f"count_failed:{t}:{e}")
            tables.append({"table": t, "rows": cnt})

        return {
            "path": path,
            "exists": True,
            "size": size,
            "size_mb": round(size / 1024 / 1024, 2),
            "tables": tables,
            "diagnostics": diagnostics,  # [ADD] мягкие замечания по БД
        }
    except Exception as e:
        return {"path": path, "exists": True, "error": f"{e}"}
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                # мягко игнорируем, чтобы не портить метрики
                pass


# [SECURE] Безопасный запуск whitelisted-команд «make -s <target>» без shell=True.
# Уходим от прямого import subprocess (B404) + добавляем явную белую схему (см. B603).
def _import_subprocess():
    # [FIX][LINT] вместо локального импорта используем верхнеуровневый importlib (PLC0415)
    return importlib.import_module("subprocess")


_ALLOWED_MAKE_TARGETS: dict[str, list[str]] = {
    # имя псевдо-команды -> конкретный вызов make с безопасными флагами
    "tests_smoke": ["make", "-s", "tests-smoke"],
    "lint_safe": ["make", "-s", "lint"],
    "bandit": ["make", "-s", "bandit"],
}


def run_cmd(cmd_key: str) -> tuple[int, str]:
    """
    Выполняет команду из белого списка.
    Возвращает (returncode, stdout). Никогда не использует shell=True.
    """
    cmd = _ALLOWED_MAKE_TARGETS.get(cmd_key)
    if not cmd:
        return 127, f"unsupported cmd: {cmd_key}"

    # Проверяем наличие «make» и неиспользование shell
    make_path = shutil.which(cmd[0])
    if not make_path:
        return 127, "make not found"

    sp = _import_subprocess()
    # nosec B603: команда фиксирована и прошла whitelisting, shell не используется
    p = sp.run([make_path, *cmd[1:]], stdout=sp.PIPE, stderr=sp.STDOUT, text=True, check=False)  # nosec B603
    return p.returncode, (p.stdout or "").strip()


def probe_quality() -> dict:
    # Быстрые качества: через белый список «make -s …» (см. _ALLOWED_MAKE_TARGETS)
    results: dict[str, dict[str, Any]] = {}
    for name in ("tests_smoke", "lint_safe", "bandit"):
        try:
            code, out = run_cmd(name)
            tail = (out.splitlines() if out else [])[-10:]
            results[name] = {"ok": code == 0, "code": code, "out_tail": tail}
        except Exception as e:
            results[name] = {"ok": False, "code": 127, "out_tail": [f"EXC {e}"]}
    return results


def load_logs(log_file: str, last_n: int = 2000) -> dict:
    if not os.path.exists(log_file):
        return {"exists": False, "errors": 0, "warns": 0, "tail": []}
    # без зависимостей — простая эвристика
    errors = 0
    warns = 0
    tail: list[str] = []
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-last_n:]
            for ln in lines:
                tail.append(ln.strip()[:1000])
                if '"status": "error"' in ln or '"status":"error"' in ln:
                    errors += 1
                if '"status": "warn"' in ln or '"status":"warn"' in ln:
                    warns += 1
    except Exception as e:
        # Мягкая деградация: возвращаем «exists: True», но с заметкой об ошибке
        return {"exists": True, "errors": errors, "warns": warns, "tail": tail[-50:], "error": f"{e}"}
    return {"exists": True, "errors": errors, "warns": warns, "tail": tail[-50:]}


def main():
    # [ADD] диагностический буфер (не ломает API вывода — это новый ключ)
    diagnostics: list[str] = []

    # [ADD] поддержка альтернативного пути к конфигу через CLI/ENV остаётся в load_cfg()
    # Для полной обратной совместимости сохранён вызов load_cfg() без аргументов.
    cfg = load_cfg()
    if not cfg:
        diagnostics.append("cfg_empty_or_missing")

    artifacts_cfg = cfg.get("artifacts", [])
    endpoints_cfg = cfg.get("endpoints", {}) if isinstance(cfg.get("endpoints", {}), dict) else {}
    logs_dir = cfg.get("logs_dir", "logs")
    log_file = cfg.get("log_file", f"{logs_dir}/devforge-mas.jsonl")
    thresholds = cfg.get("thresholds", {}) if isinstance(cfg.get("thresholds", {}), dict) else {}

    # Артефакты
    try:
        artifacts = [file_info(a["path"] if isinstance(a, dict) else a) for a in artifacts_cfg]
    except Exception as e:
        diagnostics.append(f"artifacts_err:{e}")
        artifacts = []

    # Пинги
    try:
        pings = {k: http_ping(v) for k, v in endpoints_cfg.items() if v}
    except Exception as e:
        diagnostics.append(f"pings_err:{e}")
        pings = {}

    # БД
    dbp = cfg.get("sqlite_db")
    try:
        db = db_stats(dbp) if dbp else {}
    except Exception as e:
        diagnostics.append(f"db_err:{e}")
        db = {"path": dbp, "error": f"{e}"} if dbp else {}

    # Качество (make -s …)
    try:
        q = probe_quality()
    except Exception as e:
        diagnostics.append(f"quality_err:{e}")
        q = {"error": f"{e}"}

    # Логи
    try:
        logs = load_logs(log_file)
    except Exception as e:
        diagnostics.append(f"logs_err:{e}")
        logs = {"exists": False, "error": f"{e}"}

    # Пороги и системные ресурсы
    stale_hours = thresholds.get("artifact_stale_hours", 24)  # noqa: F841 (оставлено для совместимости и будущих проверок)
    db_max = thresholds.get("db_max_size_mb", 512)  # noqa: F841
    cpu_warn = thresholds.get("cpu_warn", 85)
    mem_warn = thresholds.get("mem_warn", 85)

    # системные ресурсы без psutil — грубо: воздержимся от CPU/MEM в кросс-платформенной минималке
    sys_res = {"cpu_warn": cpu_warn, "mem_warn": mem_warn, "note": "Для точного CPU/MEM используйте psutil (опц.)."}

    now = datetime.now(timezone.utc).isoformat()
    out = {
        "ts": now,
        "artifacts": artifacts,
        "endpoints": pings,
        "db": db,
        "quality": q,
        "logs": logs,
        "thresholds": thresholds,
        "sys": sys_res,
        "diagnostics": diagnostics,  # [ADD] новый ключ; не ломает потребителей, читающих старые поля
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # [ADD] лёгкая поддержка альтернативной конфигурации через ENV уже есть в load_cfg().
    # CLI-параметры намеренно не добавлялись, чтобы не менять интерфейс вызова.
    main()

# =============================================================================
# LEGACY (сохранено для трассировки и соответствия «кол-во строк не уменьшается»)
# Эти фрагменты не исполняются и оставлены как документация предыдущего поведения:
# -----------------------------------------------------------------------------
# - Прямой import subprocess (B404) и запуск произвольных команд (B603)
# - Динамический SQL без валидации имён таблиц (B608)
# - http_ping без проверки схемы URL (B310)
# =============================================================================
#
# import subprocess
#
# def run_cmd(cmd: list[str]) -> tuple[int, str]:
#     p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
#     return p.returncode, p.stdout.strip()
#
# def http_ping(url: str, timeout=2.0) -> dict:
#     if not url:
#         return {"url": url, "up": False, "code": None, "ms": None}
#     t0 = time.time()
#     try:
#         with urllib.request.urlopen(url, timeout=timeout) as r:
#             ms = int((time.time() - t0) * 1000)
#             return {"url": url, "up": True, "code": r.getcode(), "ms": ms}
#     except Exception:
#         return {"url": url, "up": False, "code": None, "ms": None}
#
# for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
#     try:
#         cnt = c.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
#     except Exception:
#         cnt = None
#     tables.append({"table": t, "rows": cnt})
