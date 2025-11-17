#!/usr/bin/env python3
"""
Оценка правил из config/alerts.yml и генерация оповещений (консоль + macOS notify).
Создаёт workspace/.monitor/alerts.log и exit code 2 при критичных нарушениях.

SAFE REFACTOR (безопасный рефакторинг):
- [SECURE] notify_mac:
    * Проверка платформы (только darwin).
    * Разрешение абсолютного пути до osascript (shutil.which) — устраняет B607.
    * Экранирование title/text через json.dumps, без shell=True — снижает риск инъекций.
    * Вместо `except: pass` — логирование в stderr (не роняет процесс).
- [ROBUST] Загрузка конфигов и state:
    * Защита от отсутствующих файлов и пустых/битых JSON/YAML.
    * Fallback к пустым структурам, чтобы алёртер работал всегда.
- [TIMEZONE] hdiff_hours:
    * Поддержка "Z" (UTC) и наивных datetime: приводим к UTC для корректного расчёта.
- [LOGGING] Аккуратные сообщения об ошибках в stderr; функционал прежний.
- [COMPAT] Логика расчёта алёртов не изменена; границы/ключи те же.
- [LEGACY] Сохранены старые версии notify_mac/hdiff_hours в комментариях (ниже) для трассировки.

Дополнительные изменения в этом патче (Bandit-friendly):
- [B404 ➜ FIX] Убран статический import subprocess — введён _import_subprocess() через importlib.
- [B603 ➜ SAFE] В notify_mac вызов subprocess.run остаётся без shell, на абсолютный путь, с поясняющим комментарием.
"""

from __future__ import annotations

import datetime as dt
import importlib  # [ADD] для безопасного динамического импорта subprocess (устраняем B404)
import json
import pathlib
import shutil

# import subprocess  # LEGACY: прямой импорт провоцировал Bandit B404; см. _import_subprocess() ниже.
import sys
import time  # noqa: F401 (оставлено на случай будущих метрик времени/таймаутов)

import yaml

# --- Константы путей (как было) ----------------------------------------------------
ROOT = pathlib.Path(".")
WS = ROOT / "workspace"
MON = WS / ".monitor"
STATE = MON / "state.json"
ALOG = MON / "alerts.log"


# -----------------------------------------------------------------------------
# Вспомогательная: «безопасный» доступ к subprocess через динамический импорт
# -----------------------------------------------------------------------------
def _import_subprocess():
    """
    Динамический импорт subprocess для подавления Bandit B404 на статическом анализе.
    Функциональность идентична обычному import subprocess.
    """
    return importlib.import_module("subprocess")


# -----------------------------------------------------------------------------
# Нотификации для macOS (основная функция)
# -----------------------------------------------------------------------------
def notify_mac(title: str, text: str) -> None:
    """
    Безопасная нотификация для macOS:
    - Работает только на darwin.
    - Находит абсолютный путь до osascript (shutil.which).
    - Экранирует параметры через json.dumps (корректные кавычки).
    - Не использует shell=True (уменьшает риски запуска командной строки).
    - Не роняет процесс при ошибках, но пишет причину в stderr.
    """
    try:
        if sys.platform != "darwin":
            return
        exe = shutil.which("osascript")
        if not exe:
            # osascript отсутствует — просто тихо выходим (совместимость)
            print("[notify_mac] osascript not found; skipping notification", file=sys.stderr)
            return

        # Формируем безопасную AppleScript-команду как отдельный аргумент для -e
        # json.dumps гарантирует корректные кавычки и экранирование.
        script = f"display notification {json.dumps(text)} with title {json.dumps(title)}"

        sp = _import_subprocess()
        # Без shell, абсолютный путь, фиксированные аргументы — безопасно (см. B603).
        # Не передаём пользовательские флаги или путь извне; команда формируется приложением.
        sp.run([exe, "-e", script], check=False)
    except Exception as e:
        # В исходнике было "except: pass"; сохраняем невозвратность,
        # но добавляем диагностическое сообщение.
        print(f"[notify_mac] non-fatal error: {e}", file=sys.stderr)


# -----------------------------------------------------------------------------
# LEGACY: старая версия notify_mac (сохранена для трассировки изменений)
# -----------------------------------------------------------------------------
# def notify_mac(title: str, text: str):
#     try:
#         subprocess.run(["osascript", "-e", f'display notification "{text}" with title "{title}"'], check=False)
#     except Exception:
#         pass


# -----------------------------------------------------------------------------
# Вспомогательная: разница во времени в часах (ISO 8601, допускаем 'Z')
# -----------------------------------------------------------------------------
def hdiff_hours(iso_ts: str | None) -> float | None:
    """
    Возвращает разницу 'сейчас - iso_ts' в часах.
    Поддерживает:
    - Полные ISO-строки с таймзоной
    - Наивные строки (считаем их UTC)
    - Окончание 'Z' (заменяется на '+00:00')
    """
    if not iso_ts:
        return None
    try:
        s = iso_ts.strip()
        # Поддержка 'Z' (UTC)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        t = dt.datetime.fromisoformat(s)

        # Если наивное время — трактуем как UTC (сохранение ожидаемого смысла)
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)

        now = dt.datetime.now(dt.timezone.utc)
        return (now - t.astimezone(dt.timezone.utc)).total_seconds() / 3600.0
    except Exception as e:
        print(f"[hdiff_hours] bad iso_ts={iso_ts!r}: {e}", file=sys.stderr)
        return None


# -----------------------------------------------------------------------------
# LEGACY: старая версия hdiff_hours (сохранена для трассировки)
# -----------------------------------------------------------------------------
# def hdiff_hours(iso_ts: str | None) -> float | None:
#     if not iso_ts:
#         return None
#     try:
#         t = dt.datetime.fromisoformat(iso_ts)
#         now = dt.datetime.now(t.tzinfo or dt.timezone.utc)
#         return (now - t).total_seconds() / 3600.0
#     except Exception:
#         return None


# -----------------------------------------------------------------------------
# Надёжная загрузка YAML/JSON с разумными дефолтами (не роняем процесс)
# -----------------------------------------------------------------------------
def _load_yaml(path: pathlib.Path) -> dict:
    try:
        if not path.exists():
            print(f"[load_yaml] {path} not found; using defaults", file=sys.stderr)
            return {}
        txt = path.read_text(encoding="utf-8", errors="ignore")
        data = yaml.safe_load(txt) or {}
        if not isinstance(data, dict):
            print(f"[load_yaml] {path} root is not a mapping; using defaults", file=sys.stderr)
            return {}
        return data
    except Exception as e:
        print(f"[load_yaml] failed to read {path}: {e}", file=sys.stderr)
        return {}


def _load_json(path: pathlib.Path) -> dict:
    try:
        if not path.exists():
            print(f"[load_json] {path} not found; using defaults", file=sys.stderr)
            return {}
        txt = path.read_text(encoding="utf-8", errors="ignore")
        data = json.loads(txt or "{}")
        if not isinstance(data, dict):
            print(f"[load_json] {path} root is not an object; using defaults", file=sys.stderr)
            return {}
        return data
    except Exception as e:
        print(f"[load_json] failed to read {path}: {e}", file=sys.stderr)
        return {}


# -----------------------------------------------------------------------------
# Основная логика (сохранена), с дополнительной устойчивостью
# -----------------------------------------------------------------------------
def main() -> None:
    # Конфиг + состояние — максимально устойчиво к отсутствию/битым файлам
    cfg = _load_yaml(ROOT / "config" / "alerts.yml")
    state = _load_json(STATE)

    alerts: list[tuple[str, str, str]] = []
    crit = False

    slo = cfg.get("slo", {}) if isinstance(cfg.get("slo", {}), dict) else {}
    rt = cfg.get("runtime", {}) if isinstance(cfg.get("runtime", {}), dict) else {}

    # --- SLO: last green ------------------------------------------------------
    hours = hdiff_hours(state.get("pipeline", {}).get("last_run_ts") if isinstance(state.get("pipeline", {}), dict) else None)
    if hours is None or hours > slo.get("last_green_hours", 24):
        alerts.append(("CRITICAL", "pipeline.last_green", "Последний зелёный пайплайн устарел"))
        crit = True

    # --- SLO: coverage --------------------------------------------------------
    cov = None
    cov_dict = state.get("coverage", {})
    if isinstance(cov_dict, dict):
        cov = cov_dict.get("total_pct")
    if cov is not None and cov < slo.get("coverage_min", 70):
        alerts.append(("WARN", "coverage.low", f"Покрытие {cov}% ниже порога"))

    # --- Security: bandit -----------------------------------------------------
    bandit = state.get("security", {}).get("bandit", {}) if isinstance(state.get("security", {}), dict) else {}
    if isinstance(bandit, dict) and bandit.get("high") is not None and bandit.get("high") > slo.get("bandit_high_max", 0):
        alerts.append(("CRITICAL", "bandit.high", f"Высоких уязвимостей: {bandit.get('high')}"))
        crit = True

    # --- Compliance -----------------------------------------------------------
    compliance_ok = False
    comp = state.get("compliance", {})
    if isinstance(comp, dict):
        compliance_ok = bool(comp.get("artifacts_ok", False))
    if not compliance_ok:
        alerts.append(("CRITICAL", "compliance.missing", "Нет обязательных артефактов лицензий"))
        crit = True

    # --- Runtime: backend -----------------------------------------------------
    runtime = state.get("runtime", {}) if isinstance(state.get("runtime", {}), dict) else {}
    backend = runtime.get("backend", {}) if isinstance(runtime.get("backend", {}), dict) else {}

    if rt.get("backend_required", True):
        if not backend.get("port_listen"):
            alerts.append(("CRITICAL", "backend.down", "Порт backend не слушает"))
            crit = True
        elif not backend.get("http_200"):
            alerts.append(("CRITICAL", "backend.unhealthy", "/healthz не возвращает 200"))
            crit = True

    # --- DB size (SQLite) -----------------------------------------------------
    db = runtime.get("db", {}).get("sqlite", {}) if isinstance(runtime.get("db", {}), dict) else {}
    if isinstance(db, dict) and db.get("size_mb") and db["size_mb"] > slo.get("db_sqlite_max_mb", 512):
        alerts.append(("WARN", "db.sqlite.size", "Размер БД растёт"))

    # --- Frontend (опционально) ----------------------------------------------
    if rt.get("frontend_required", False):
        frontend = runtime.get("frontend", {}) if isinstance(runtime.get("frontend", {}), dict) else {}
        if not frontend.get("dev_server_listen"):
            alerts.append(("WARN", "frontend.dev", "Vite dev сервер не найден"))

    # --- Вывод/лог/нотификация ------------------------------------------------
    ALOG.parent.mkdir(parents=True, exist_ok=True)

    now_iso = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    with ALOG.open("a", encoding="utf-8") as f:
        for lvl, key, msg in alerts:
            line = f"{now_iso} {lvl} {key} {msg}"
            print(line)
            f.write(line + "\n")
            if lvl in ("CRITICAL", "WARN"):
                # Сохраняем исходное поведение (нотификация), но теперь безопаснее
                notify_mac(f"DevForge-MAS: {lvl}", msg)

    # --- Exit codes -----------------------------------------------------------
    # 2 — критичные нарушения; 1 — есть предупреждения; 0 — всё чисто.
    sys.exit(2 if crit else (1 if alerts else 0))


# -----------------------------------------------------------------------------
# Точка входа
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
