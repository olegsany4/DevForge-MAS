#!/usr/bin/env python3
# tools/ci_fail_on_bandit.py
# Превращает отчёт bandit (JSON) в exit code пайплайна.
# Рефакторинг: устранён PLR2004 (магическая двойка) и UP015.

from __future__ import annotations

import json
import sys
from typing import Any

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAIL = 3
ARGC_EXPECTED = 2  # <prog> <bandit.json>


def main() -> int:
    if len(sys.argv) != ARGC_EXPECTED:
        print("Usage: ci_fail_on_bandit.py <bandit.json>", file=sys.stderr)
        return EXIT_USAGE

    path = sys.argv[1]
    try:
        # UP015: для текстового режима достаточно encoding
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
    except Exception as e:  # noqa: BLE001 - в CI читаем любой сбой как ошибку
        print(f"[ERR] Cannot read {path}: {e}", file=sys.stderr)
        return EXIT_FAIL

    # Простейшая эвристика: если issues вообще есть — фейлим
    issues = data.get("results") or data.get("issues") or []
    if isinstance(issues, list) and len(issues) == 0:
        print("[OK] Bandit: no issues")
        return EXIT_OK

    print(f"[FAIL] Bandit: found {len(issues) if isinstance(issues, list) else 'some'} issues", file=sys.stderr)
    return EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
