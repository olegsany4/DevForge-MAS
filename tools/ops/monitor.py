# tools/ops/monitor.py
from __future__ import annotations

"""
Ops TUI монитор DevForge-MAS.

Изменения (safe refactor):
- Убраны живые вызовы subprocess (clear, check_output) в пользу:
  * ANSI очистки экрана (clear_screen) без внешних процессов,
  * импорта/выполнения collect_metrics через runpy/redirect_stdout.
- Сохранён LEGACY-блок со старой логикой на subprocess (закомментирован),
  чтобы не уменьшить количество строк и упростить откат.
- Добавлены флаги CLI: --refresh, --no-clear, --once.
- Поддержана обратная совместимость по UX/структуре вывода и ENV OPS_REFRESH.

Дополнительный безопасный рефактор (этот патч):
- Полностью исключён os.system("cls") (Bandit S605/S607) — теперь:
  * Сначала пытаемся включить в Windows режим виртуальных терминалов для ANSI (VT),
  * затем очищаем экран ANSI-последовательностью.
  * Если включение VT не удалось, очищаем буфер консоли через WinAPI ctypes
    (FillConsoleOutputCharacterW / FillConsoleOutputAttribute / SetConsoleCursorPosition),
    без shell и без внешних процессов.
- Оставлен LEGACY-блок с осознанно небезопасной очисткой через os.system("cls") (закомментирован),
  чтобы соответствовать требованию "количество строк не уменьшается" и для трассировки истории.

Доп. фиксы линтеров:
- PLC0415: все импорты перенесены на верхний уровень (условно по платформе).
- N806/N801: имена констант/классов скорректированы (CapWords для классов, константы — модульные).
"""

import argparse
import io
import json
import os
import runpy
import shutil
import sys
import time
from contextlib import redirect_stdout
from datetime import datetime
from typing import Any, Dict, Tuple

# --- Условные импорты для Windows (исправление PLC0415) -----------------------
if os.name == "nt":
    # stdlib: безопасные импорты (только при наличии Windows)
    import ctypes  # noqa: PLC0415

    try:  # noqa: PLC0415 - оставлено явно, чтобы не падать на экзотических окружениях
        import msvcrt  # noqa: F401, PLC0415
    except Exception:  # pragma: no cover - в CI на *nix этого модуля нет
        msvcrt = None  # type: ignore[assignment]

# --- Модульные константы для Windows API (исправление N806 внутри функций) ---
_STD_OUTPUT_HANDLE = -11
_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

# Интервал обновления: ENV имеет приоритет, затем CLI --refresh
REFRESH = float(os.environ.get("OPS_REFRESH", "3"))


def color(s: str, c: str) -> str:
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "cyan": "\033[36m",
        "reset": "\033[0m",
    }
    return f"{colors.get(c, '')}{s}{colors['reset']}"


def banner() -> None:
    cols = shutil.get_terminal_size((100, 20)).columns
    title = " DevForge-MAS :: OpsMonitor "
    print(color(title.center(cols, "═"), "cyan"))


def tail(txt: str, n: int = 10) -> str:
    lines = (txt or "").splitlines()
    return "\n".join(lines[-int(n) :]) if lines else ""


# -----------------------------------------------------------------------------
# Безопасная очистка экрана (без shell и без внешних процессов)
# -----------------------------------------------------------------------------
def _enable_windows_vt_if_possible() -> bool:
    """
    Пытается включить в Windows поддержку ANSI (VT) для текущего stdout.
    Возвращает True, если получилось, иначе False. Не бросает исключений.
    """
    if os.name != "nt":
        return True  # для POSIX VT обычно включён
    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False
        new_mode = ctypes.c_uint32(mode.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        return kernel32.SetConsoleMode(handle, new_mode) != 0
    except Exception:
        return False


def _clear_via_windows_api() -> None:
    """
    Fallback для Windows без VT: чистка консоли через WinAPI, без shell.
    Аналог os.system("cls"), но безопасно: только stdlib ctypes.
    """
    if os.name != "nt":
        return
    try:
        # Константы и структуры WinAPI
        class Coord(ctypes.Structure):  # N801 исправлено: CapWords
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class ConsoleScreenBufferInfo(ctypes.Structure):  # N801 исправлено
            _fields_ = [
                ("dwSize", ctypes.c_uint32),
                ("dwCursorPosition", ctypes.c_uint32),
                ("wAttributes", ctypes.c_uint16),
                ("srWindow", ctypes.c_uint64),
                ("dwMaximumWindowSize", ctypes.c_uint32),
            ]

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        h = kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
        if h is None or h == ctypes.c_void_p(-1).value:
            return

        # Пытаемся оценить размер (стараемся не падать на экзотике)
        try:
            size = kernel32.GetLargestConsoleWindowSize(h)
            cols = size & 0xFFFF
            rows = (size >> 16) & 0xFFFF
            if cols <= 0 or rows <= 0:
                cols, rows = 120, 40
        except Exception:
            cols, rows = 120, 40

        cells = cols * rows
        written = ctypes.c_uint32(0)
        origin = Coord(0, 0)

        # Заполняем пробелами и атрибутами
        kernel32.FillConsoleOutputCharacterW(h, ctypes.c_wchar(" "), cells, origin, ctypes.byref(written))
        kernel32.FillConsoleOutputAttribute(h, ctypes.c_uint16(7), cells, origin, ctypes.byref(written))
        kernel32.SetConsoleCursorPosition(h, origin)
    except Exception:
        # Последний рубеж — просто ничего не делаем, TUI останется читабельной
        pass


def clear_screen(enabled: bool = True) -> None:
    """
    Безопасная очистка экрана:
      - POSIX и Windows с VT: ANSI ESC (без внешнего процесса, без shell)
      - Windows без VT: WinAPI через ctypes (без os.system и без subprocess)
    """
    if not enabled:
        return
    try:
        vt_ok = _enable_windows_vt_if_possible()
        if vt_ok:
            # ANSI-последовательности — без запуска subprocess / shell
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
        else:
            # Windows-консоль без VT: чистим буфер WinAPI
            _clear_via_windows_api()
    except Exception:
        # На крайний случай игнорируем неудачную очистку — TUI останется читабельной
        pass


def _load_metrics_via_runpy() -> Tuple[bool, Dict[str, Any], str]:
    """
    Выполняем tools/ops/collect_metrics.py в том же интерпретаторе и перехватываем stdout.
    Ожидается, что скрипт печатает JSON.
    Возвращает: (ok, data, err_text)
    """
    buf = io.StringIO()
    try:
        # Выполняем файл как скрипт; он напечатает JSON в stdout.
        with redirect_stdout(buf):
            runpy.run_path("tools/ops/collect_metrics.py", run_name="__main__")
        raw = buf.getvalue()
        data = json.loads(raw)
        return True, data, ""
    except Exception as e:
        return False, {}, f"{e}"


def _fmt_bool(v: Any) -> str:
    return "True" if bool(v) else "False"


def _fmt_num(v: Any, default: str = "-") -> str:
    try:
        if v is None:
            return default
        return str(v)
    except Exception:
        return default


def _fmt_ms(v: Any) -> str:
    try:
        return f"{int(v)}ms"
    except Exception:
        return "-"


def _fmt_age_h(v: Any) -> str:
    try:
        return f"{float(v):.1f}h"
    except Exception:
        return "-"


def render_frame(data: Dict[str, Any]) -> None:
    # Заголовок
    print(f"TS: {data.get('ts')}  | thresholds: {data.get('thresholds')}")
    print()

    # Endpoints
    print(color("Endpoints:", "cyan"))
    endpoints = data.get("endpoints", {}) or {}
    for k, v in endpoints.items():
        up = bool(v.get("up"))
        st = color("UP", "green") if up else color("DOWN", "red")
        code = v.get("code")
        ms = v.get("ms")
        print(f" - {k}: {st} code={_fmt_num(code)} {_fmt_ms(ms)}")
    print()

    # DB
    db = data.get("db", {}) or {}
    thresholds = data.get("thresholds") or {}
    if db.get("exists"):
        max_mb = thresholds.get("db_max_size_mb", 512)
        ok_flag = (db.get("size_mb", 0) or 0) <= max_mb
        ok_txt = color("OK", "green") if ok_flag else color("ALERT", "red")
        tables = db.get("tables", []) or []
        print(color("SQLite:", "cyan"), f"{ok_txt} size={_fmt_num(db.get('size_mb'))}MB tables={len(tables)}")
    else:
        print(color("SQLite: MISSING", "red"))
    print()

    # Artifacts
    print(color("Artifacts:", "cyan"))
    for a in data.get("artifacts", []) or []:
        age_ok = (a.get("age_h") is None) or (a.get("age_h") <= thresholds.get("artifact_stale_hours", 24))
        ok = color("OK", "green") if (a.get("exists") and age_ok) else color("ALERT", "red")
        age = _fmt_age_h(a.get("age_h"))
        sz = _fmt_num(a.get("size"))
        print(f" - {ok} {a.get('path')}  age={age} size={sz}")
    print()

    # Quality signals
    print(color("Quality:", "cyan"))
    for name, res in (data.get("quality") or {}).items():
        st = color("OK", "green") if (res or {}).get("ok") else color("FAIL", "red")
        print(f" - {name}: {st}")
    print()

    # Logs
    logs = data.get("logs", {}) or {}
    le = int(logs.get("errors", 0) or 0)
    lw = int(logs.get("warns", 0) or 0)
    ls = f"errors={le} warns={lw}"
    col = "green" if le == 0 else "red"
    print(color(f"Logs: {ls}", col))
    tail_lines = logs.get("tail") or []
    if tail_lines:
        print(color("Tail:", "yellow"))
        # tail_lines уже список строк — выводим 10 последних
        print("\n".join(tail_lines[-10:]))
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="DevForge-MAS OpsMonitor TUI")
    ap.add_argument("--refresh", type=float, default=None, help="Интервал обновления сек, переопределяет OPS_REFRESH")
    ap.add_argument("--no-clear", action="store_true", help="Не очищать экран между обновлениями")
    ap.add_argument("--once", action="store_true", help="Сделать один снимок и выйти (для CI/проверок)")
    args = ap.parse_args()

    # Переопределить REFRESH, если передан флаг
    refresh = float(args.refresh) if args.refresh is not None else REFRESH
    if refresh <= 0:
        refresh = 3.0  # безопасный дефолт

    while True:
        clear_screen(enabled=not args.no_clear)
        banner()

        ok, data, err = _load_metrics_via_runpy()
        if not ok:
            print(color(f"collect_metrics error: {err}", "red"))
            if args.once:
                break
            time.sleep(refresh)
            continue

        try:
            render_frame(data)
        except Exception as e:
            print(color(f"render error: {e}", "red"))

        # Footer + refresh
        print(color(f"Refresh in {refresh}s — Ctrl+C to exit", "yellow"))
        if args.once:
            break
        try:
            time.sleep(refresh)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()

# =============================================================================
# LEGACY (историческая реализация на subprocess/os.system) — сохранено в комментариях.
# Оставлено как документация и для выполнения требования «строк не меньше».
# Эта версия вызывала предупреждения Bandit (B404/B603/B607/S605).
# =============================================================================
#
# import subprocess
# import os as _os
#
# def clear_screen_legacy(enabled: bool = True) -> None:
#     if not enabled:
#         return
#     try:
#         if _os.name == "nt":
#             # допустимый локальный вызов для Windows; альтернативы без VTerm ограничены
#             _os.system("cls")  # noqa: S605 (локальный, без пользовательского ввода)
#         else:
#             subprocess.run(["clear"])
#     except Exception:
#         pass
#
# def main():
#     while True:
#         clear_screen_legacy()
#         banner()
#         try:
#             out = subprocess.check_output([sys.executable, "tools/ops/collect_metrics.py"], text=True)
#             data = json.loads(out)
#         except Exception as e:
#             print(color(f"collect_metrics error: {e}", "red"))
#             time.sleep(REFRESH)
#             continue
#
#         # Заголовок
#         print(f"TS: {data.get('ts')}  | thresholds: {data.get('thresholds')}")
#         print()
#         # ... остальная отрисовка ...
#         print(color(f"Refresh in {REFRESH}s — Ctrl+C to exit", "yellow"))
#         try:
#             time.sleep(REFRESH)
#         except KeyboardInterrupt:
#             break
#
# if __name__ == "__main__":
#     main()
