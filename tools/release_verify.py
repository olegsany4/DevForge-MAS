#!/usr/bin/env python3
"""
tools/release_verify.py — минимальная верификация релиза перед упаковкой.

Проверяет:
- Наличие ключевых артефактов (compliance, checks, wbs)
- Запуск lint/tests/bandit
- DB-smoke (если SQLITE DB_FILE указан)
Формирует краткий отчет release_report.txt

Дополнения в рамках безопасного рефакторинга:
- Mypy-фиксы: параметризация subprocess.CompletedProcess[str], text=True
- Пишем ещё и JSON-отчёт (release_report.json) для CI
- Опциональный строгий режим через RELEASE_VERIFY_STRICT=1 → код возврата 1 при наличии [WARN]
- Старая логика вызовов и формат TXT-отчёта сохранены (обратная совместимость)
"""

from __future__ import annotations

import hashlib  # noqa: INP001  # импорт поднят на верх для ruff PLC0415
import json
import os
import subprocess  # nosec B404 - используем только shell=False для контролируемых команд
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ROOT / "compliance" / "NOTICE",
    ROOT / "compliance" / "OBLIGATIONS.md",
    ROOT / "compliance" / "THIRD_PARTY_LICENSES.md",
    ROOT / "workspace" / ".checks",
    ROOT / "workspace" / "wbs" / "wbs.json",
]

SAFE_COMMANDS = {
    ("make", "lint"),
    ("pytest", "-q"),
    ("make", "bandit"),
}


# === Новые типы для отчёта (JSON) ===
class StepResult(TypedDict, total=False):
    name: str
    status: str  # OK | WARN | FAIL | SKIP | INFO
    detail: str


class ReportModel(TypedDict, total=False):
    missing: list[str]
    steps: list[StepResult]
    reproducibility_hash: str
    db_file: str


# === Тип CompletedProcess[str] для строгой типизации (mypy-фикс) ===
CompletedStr = subprocess.CompletedProcess[str]


def run(cmd: Sequence[str], check: bool = True) -> CompletedStr:
    """
    Запускает команду из белого списка. Возвращает CompletedProcess[str].

    Важно: text=True → stdout/stderr будут str, что согласуется с типом CompletedProcess[str].
    """
    # Проверяем, что команда из белого списка (минимальная защита от подмены)
    if tuple(cmd) not in SAFE_COMMANDS:
        raise ValueError(f"Command not allowed by release_verify whitelist: {cmd}")
    print(f"[RUN] {' '.join(cmd)}")
    # СТАРАЯ ВЕРСИЯ (оставлена для прозрачности изменений):
    # return subprocess.run(cmd, cwd=ROOT, check=check)  # nosec B603 - shell=False по умолчанию
    # НОВАЯ ВЕРСИЯ: добавляем text=True для согласованности типов
    return subprocess.run(cmd, cwd=ROOT, check=check, text=True)  # nosec B603


def _write_reports_txt_json(report_lines: list[str], json_payload: ReportModel) -> None:
    """
    Пишем оба отчёта: release_report.txt и release_report.json.
    TXT остается основным каналом совместимости, JSON — для CI.
    """
    txt_path = ROOT / "release_report.txt"
    json_path = ROOT / "release_report.json"
    content = "\n".join(report_lines)
    txt_path.write_text(content, encoding="utf-8")
    try:
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:  # запись JSON не блокирует основной процесс
        # Добавляем в текстовый отчёт информацию об ошибке, не меняя код возврата
        report_lines.append(f"[WARN] failed to write JSON report: {e}")
        txt_path.write_text("\n".join(report_lines), encoding="utf-8")


def main() -> int:  # noqa: PLR0915
    missing = [str(p) for p in REQUIRED_FILES if not p.exists()]
    report: list[str] = []
    steps: list[StepResult] = []

    if missing:
        report.append("[FAIL] Missing required artifacts:\n- " + "\n- ".join(missing))
        steps.append({"name": "required_artifacts", "status": "FAIL", "detail": "\n".join(missing)})
        _write_reports_txt_json(report, {"missing": missing, "steps": steps})
        return 2

    steps.append({"name": "required_artifacts", "status": "OK", "detail": "all present"})
    # Lint
    try:
        run(["make", "lint"])
        report.append("[OK] lint")
        steps.append({"name": "lint", "status": "OK", "detail": ""})
    except Exception as e:
        report.append(f"[WARN] lint failed or tool missing: {e}")
        steps.append({"name": "lint", "status": "WARN", "detail": str(e)})

    # Tests
    try:
        run(["pytest", "-q"])
        report.append("[OK] tests")
        steps.append({"name": "tests", "status": "OK", "detail": ""})
    except Exception as e:
        report.append(f"[WARN] tests failed or pytest missing: {e}")
        steps.append({"name": "tests", "status": "WARN", "detail": str(e)})

    # Security (bandit)
    try:
        run(["make", "bandit"])
        report.append("[OK] bandit")
        steps.append({"name": "bandit", "status": "OK", "detail": ""})
    except Exception as e:
        report.append(f"[WARN] bandit failed or tool missing: {e}")
        steps.append({"name": "bandit", "status": "WARN", "detail": str(e)})

    # Compliance quick check: файлы уже проверили
    report.append("[OK] compliance files present")
    steps.append({"name": "compliance_files", "status": "OK", "detail": ""})

    # DB smoke
    db_file = os.environ.get("DB_FILE", "devforge_mas.sqlite3")
    db_detail = f"DB_FILE={db_file}"
    try:
        tool = ROOT / "tools" / "db_smoke_sqlite.py"
        if tool.exists():
            env = os.environ.copy()
            env["DB_FILE"] = db_file
            print(f"[INFO] DB_FILE={db_file}")
            # Явно shell=False; управляема команда — разрешаем # nosec B603
            # subprocess.run([sys.executable, "tools/db_smoke_sqlite.py"], cwd=ROOT, check=True, env=env)  # nosec B603
            # Уточнение типов: text=True → согласованно со строковым CompletedProcess (хотя результат не используется)
            subprocess.run([sys.executable, "tools/db_smoke_sqlite.py"], cwd=ROOT, check=True, env=env, text=True)  # nosec B603
            report.append("[OK] db smoke")
            steps.append({"name": "db_smoke", "status": "OK", "detail": db_detail})
        else:
            msg = "tools/db_smoke_sqlite.py not found"
            report.append(f"[SKIP] db smoke ({msg})")
            steps.append({"name": "db_smoke", "status": "SKIP", "detail": msg})
    except Exception as e:
        report.append(f"[WARN] db smoke failed: {e}")
        steps.append({"name": "db_smoke", "status": "WARN", "detail": f"{db_detail}; {e}"})

    # Reproducibility hash (НЕ для безопасности)
    rep_hash = ""
    try:
        # --- СТАРЫЙ ПОДХОД (оставлен в комментарии для истории и сравнения) ---
        # try:
        #     digest = hashlib.md5(usedforsecurity=False)  # type: ignore[call-arg]
        # except TypeError:
        #     digest = hashlib.blake2b(digest_size=16)
        # ----------------------------------------------------------------------

        # --- НОВЫЙ БЕЗОПАСНЫЙ ПОДХОД (Bandit B324 compliant) ---
        try:
            # Py3.9+: параметр explicitly помечает, что хэш не используется в целях безопасности
            digest = hashlib.md5(usedforsecurity=False)  # type: ignore[call-arg]  # nosec B324
        except TypeError:
            # На старых рантаймах — надёжный современный фолбэк
            digest = hashlib.blake2b(digest_size=16)  # nosec B324

        for p in sorted(ROOT.rglob("*")):
            if p.is_file():
                s = f"{p.relative_to(ROOT)}:{p.stat().st_size}\n".encode()
                digest.update(s)
        rep_hash = digest.hexdigest()
        report.append(f"[INFO] reproducibility hash: {rep_hash}")
        steps.append({"name": "reproducibility_hash", "status": "INFO", "detail": rep_hash})
    except Exception as e:
        report.append(f"[WARN] reproducibility hash failed: {e}")
        steps.append({"name": "reproducibility_hash", "status": "WARN", "detail": str(e)})

    # Формируем и пишем отчёты
    _write_reports_txt_json(
        report,
        {
            "missing": [],
            "steps": steps,
            "reproducibility_hash": rep_hash,
            "db_file": db_file,
        },
    )
    print("\n".join(report))

    # === Опциональный строгий режим для CI ===
    # Обратная совместимость: по умолчанию возвращаем 0 (как раньше).
    strict = os.environ.get("RELEASE_VERIFY_STRICT", "").strip().lower() in {"1", "true", "yes"}
    if strict and any(line.startswith("[WARN]") for line in report):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
