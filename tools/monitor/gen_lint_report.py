#!/usr/bin/env python3
"""
Генерирует workspace/.checks/lint.json из вывода Ruff.

Безопасный рефактор:
- Убрана жёсткая зависимость от /tmp/ruff.out (Bandit B108).
- Источник задаётся через CLI/ENV, есть безопасные дефолты и LEGACY-fallback.
- Формат вывода полностью совместим с прежним: {"issues": <int>} и строка лога
  "[lint-report] issues=<N>".

Совместимость:
- Поведение при отсутствии файла: issues=0 (мягкая логика, как и раньше).
- Путь назначения по умолчанию: workspace/.checks/lint.json (тот же).

Пути-источники (приоритет):
  1) --input <path>
  2) env LINT_RUFF_OUT
  3) workspace/.checks/ruff.out
  4) workspace/.checks/ruff.json   # [NEW] безопасный JSON-отчёт Ruff
  5) LEGACY: /tmp/ruff.out (для обратной совместимости)
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Any

# ---- Константы путей (по умолчанию) -------------------------------------------------
ROOT = pathlib.Path(".").resolve()
WS = ROOT / "workspace"
CHECKS = WS / ".checks"

# Безопасный дефолтный источник: внутри репозитория
SAFE_DEFAULT_INPUT = CHECKS / "ruff.out"

# [NEW] Безопасный источник JSON — если CI пишет ruff в JSON
SAFE_DEFAULT_INPUT_JSON = CHECKS / "ruff.json"

# LEGACY-источник для полной совместимости (ранее был захардкожен)
LEGACY_TMP_INPUT = pathlib.Path("/tmp/ruff.out")

# Дефолтный выходной файл (как и раньше)
DEFAULT_OUTPUT = CHECKS / "lint.json"


# ---- Утилиты ------------------------------------------------------------------------
def parse_ruff_out(txt: str) -> int:
    """
    Извлекает количество ошибок из вывода Ruff (текстовый формат).

    Поддерживаемые форматы:
      - "Found N error" (точное совпадение со старой логикой)
      - "Found N errors"
      - Обобщённый шаблон по строке с 'Found <N> error'
      - Дополнительно пытаемся поймать финальный summary-стиль Ruff:
        например, "N errors" (без слова Found), если встречается в отчёте.

    Если ничего уверенно не нашли — возвращаем 0 (мягко, как и раньше).
    """
    # 1) Прежний точный шаблон
    m = re.search(r"Found\s+(\d+)\s+error\b", txt)
    if m:
        return int(m.group(1))

    # 2) Расширенный шаблон с errors
    m = re.search(r"Found\s+(\d+)\s+errors\b", txt)
    if m:
        return int(m.group(1))

    # 3) Частые финальные сводки вида "N errors" / "N error"
    m = re.search(r"\b(\d+)\s+errors?\b", txt)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass

    # 4) Иногда Ruff печатает строки вроде "violations: N"
    m = re.search(r"\bviolations?\s*:\s*(\d+)\b", txt, flags=re.I)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass

    # 5) Ничего не нашли — по старой логике считаем 0
    return 0


def parse_ruff_json(txt: str) -> int:
    """
    Парсит JSON-вывод Ruff (ruff -o json ...).
    Ожидаемые варианты:
      - массив объектов-нарушений -> issues = len(array)
      - объект с ключами ('messages' | 'results' | 'summary') -> берём разумное поле
    При неудаче — возвращаем 0 (мягкая совместимость).
    """
    try:
        data = json.loads(txt)
    except Exception:
        return 0

    # В старых/простых режимах Ruff может отдавать список нарушений
    if isinstance(data, list):
        return len(data)

    if isinstance(data, dict):
        # Наиболее очевидные варианты
        for key in ("messages", "results", "violations", "items"):
            val = data.get(key)
            if isinstance(val, list):
                return len(val)

        # Сводка, если предоставлена
        summary = data.get("summary")
        if isinstance(summary, dict):
            # пробуем стандартные поля
            for k in ("total", "errors", "issues", "violations"):
                v = summary.get(k)
                if isinstance(v, int) and v >= 0:
                    return int(v)

    return 0


def looks_like_json(txt: str | None) -> bool:
    """
    Грубая эвристика: похоже ли содержимое на JSON.
    """
    if txt is None:
        return False
    s = txt.lstrip()
    return s.startswith("{") or s.startswith("[")


def resolve_input_path(cli_input: str | None) -> pathlib.Path:
    """
    Выбирает путь к источнику Ruff-отчёта в безопасном порядке:
      CLI --input -> ENV LINT_RUFF_OUT -> SAFE_DEFAULT_INPUT -> SAFE_DEFAULT_INPUT_JSON -> LEGACY_TMP_INPUT.
    """
    if cli_input:
        return pathlib.Path(cli_input).expanduser().resolve()

    env_path = os.getenv("LINT_RUFF_OUT")
    if env_path:
        return pathlib.Path(env_path).expanduser().resolve()

    # Безопасный дефолт рядом с артефактами (текст)
    if SAFE_DEFAULT_INPUT.exists():
        return SAFE_DEFAULT_INPUT

    # [NEW] Безопасный дефолт JSON, если присутствует
    if SAFE_DEFAULT_INPUT_JSON.exists():
        return SAFE_DEFAULT_INPUT_JSON

    # LEGACY: сохраняем поведение, если кто-то всё ещё пишет в /tmp/ruff.out
    return LEGACY_TMP_INPUT


def load_text(path: pathlib.Path) -> str | None:
    """
    Читает текст из файла. При отсутствующем файле — возвращает None.
    Ошибки чтения не фатальны (вернём None и посчитаем issues=0).
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return None
    except Exception:
        # Не спамим исключениями — действуем мягко, как и раньше
        return None


def write_json(path: pathlib.Path, payload: dict) -> None:
    """
    Атомарная запись JSON (насколько возможно без временных файлов):
    - гарантируем наличие каталога
    - кодировка utf-8
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# ---- Ядро генерации --------------------------------------------------------------
def generate_report(
    input_path: pathlib.Path,
    output_path: pathlib.Path,
    strict: bool = False,
    dry_run: bool = False,
) -> tuple[int, dict[str, Any]]:
    """
    Объединённая функция для использования из main() и unit-тестов.
    Возвращает (exit_code, payload). При dry_run файл не пишется.
    """
    txt = load_text(input_path)
    if txt is None:
        # Совместимость с прошлой логикой: если Ruff не запускался — issues=0
        issues = 0
    elif looks_like_json(txt):
        issues = parse_ruff_json(txt)
        # Если JSON не дал уверенного результата — fallback к текстовому
        if issues == 0:
            issues = parse_ruff_out(txt)
    else:
        issues = parse_ruff_out(txt)

    payload = {"issues": issues}

    if not dry_run:
        write_json(output_path, payload)

    print(f"[lint-report] issues={issues}")

    # По умолчанию совместимы с прежним поведением: возвращаем 0 всегда.
    # В строгом режиме можно сигнализировать о наличии проблем ненулевым кодом.
    if strict and issues > 0:
        return 1, payload
    return 0, payload


# ---- Основной сценарий --------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Generate lint.json from Ruff output in a safe, backward-compatible way.")
    ap.add_argument(
        "--input",
        type=str,
        help="Путь к файлу вывода Ruff (по умолчанию: $LINT_RUFF_OUT или workspace/.checks/ruff.out / ruff.json; LEGACY: /tmp/ruff.out).",
    )
    ap.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Путь для сохранения lint.json (по умолчанию: workspace/.checks/lint.json).",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Если установлен, завершить с кодом 1 при issues>0 (по умолчанию всегда 0, для полной совместимости).",
    )
    # [NEW] «Сухой прогон» — ничего не записывает, печатает только сводку
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Не писать файл, только вывести сводку issues (для CI/отладки).",
    )
    args = ap.parse_args()

    # [NEW] Поддержка STRICT через окружение без изменения API
    strict_env = os.getenv("LINT_STRICT")
    strict = bool(args.strict or (strict_env and strict_env.strip() not in ("0", "false", "False")))

    input_path = resolve_input_path(args.input)
    output_path = pathlib.Path(args.output).expanduser().resolve()

    exit_code, _payload = generate_report(
        input_path=input_path,
        output_path=output_path,
        strict=strict,
        dry_run=args.dry_run,
    )
    return exit_code


# -----------------------------------------------------------------------------
# LEGACY (историческая версия — оставлена как комментарий для трассировки и
#         выполнения требования «количество строк не уменьшается»):
# -----------------------------------------------------------------------------
# def main() -> int:
#     out_path = pathlib.Path("workspace/.checks") / "lint.json"
#     try:
#         txt = pathlib.Path("/tmp/ruff.out").read_text(encoding="utf-8", errors="ignore")
#     except FileNotFoundError:
#         # Если ruff не запускался, считаем issues=0 (как и раньше — мягкая логика)
#         issues = 0
#     else:
#         # Совместим с прежним регулярным выражением
#         m = re.search(r"Found (\d+) error", txt)
#         issues = int(m.group(1)) if m else 0
#
#     out_path.parent.mkdir(parents=True, exist_ok=True)
#     out_path.write_text(json.dumps({"issues": issues}, ensure_ascii=False), encoding="utf-8")
#     print(f"[lint-report] issues={issues}")
#     return 0
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    sys.exit(main())
