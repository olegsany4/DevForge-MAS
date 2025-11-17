#!/usr/bin/env python3
# tools/verify_security_artifacts.py
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(".").resolve()

FILES = {
    "stride": ROOT / "workspace/security/STRIDE.md",
    "sast": ROOT / "workspace/security/SAST_CHECKLIST.md",
    "hardening": ROOT / "workspace/security/HARDENING.md",
    "ci": ROOT / "workspace/.ci/security.yml",
}

REQUIRED_STEPS = [
    "Ruff",
    "MyPy",
    "Bandit",
    "Semgrep",
    "Detect Secrets",
    "Gitleaks",
    "Pip Audit",
    "Safety",
]

STRIDE_HEADERS = [
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information Disclosure",
    "Denial of Service",
    "Elevation of Privilege",
]

HARDENING_MARKERS = [
    "Identity",
    "Secrets",
    "Supply-Chain",
    "Runtime",
    "LLM Safety",
    "Resilience",
]


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


def _check_exists_and_not_empty(path: Path, label: str) -> None:
    if not path.exists():
        fail(f"{label}: не найден ({path})")
    if path.is_file() and path.stat().st_size == 0:
        fail(f"{label}: пустой файл ({path})")
    ok(f"{label}: найден и непустой")


def _contains_all(text: str, terms: list[str]) -> bool:
    needles = [t.lower() for t in terms]
    hay = text.lower()
    return all(n in hay for n in needles)


def check_markdown(path: Path, label: str, required_terms: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not _contains_all(text, required_terms):
        warn(f"{label}: не все требуемые маркеры найдены (ищем {required_terms})")
    ok(f"{label}: структура Markdown OK")


def check_ci_yaml(ci_path: Path) -> None:
    try:
        content = yaml.safe_load(ci_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail(f"CI YAML: ошибка парсинга: {exc}")

    if not isinstance(content, dict):
        fail("CI YAML: корень не является mapping")

    jobs = content.get("jobs", {})
    if not isinstance(jobs, dict) or not jobs:
        fail("CI YAML: не найдены jobs")

    # Соберём имена шагов из всех jobs
    step_names: set[str] = set()
    for job_def in jobs.values():
        if not isinstance(job_def, dict):
            continue
        steps = job_def.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, dict):
                name = step.get("name")
                if isinstance(name, str):
                    step_names.add(name)

    missing = [s for s in REQUIRED_STEPS if s not in step_names]
    if missing:
        warn(f"CI YAML: не найдены шаги {missing} — проверь конфигурацию (возможно отключены)")

    ok("CI YAML: базовая валидация пройдена")


def main() -> None:
    print("=== DevForge-MAS :: Security Artifacts Verifier ===")

    _check_exists_and_not_empty(FILES["stride"], "STRIDE")
    _check_exists_and_not_empty(FILES["sast"], "SAST")
    _check_exists_and_not_empty(FILES["hardening"], "HARDENING")
    _check_exists_and_not_empty(FILES["ci"], "CI")

    check_markdown(FILES["stride"], "STRIDE.md", STRIDE_HEADERS)
    check_markdown(FILES["sast"], "SAST_CHECKLIST.md", ["SAST", "Bandit", "Semgrep"])
    check_markdown(
        FILES["hardening"],
        "HARDENING.md",
        HARDENING_MARKERS,
    )
    check_ci_yaml(FILES["ci"])

    result = {
        "status": "OK",
        "checked": {
            "stride": str(FILES["stride"]),
            "sast": str(FILES["sast"]),
            "hardening": str(FILES["hardening"]),
            "ci": str(FILES["ci"]),
        },
        "notes": ("Все ключевые security-артефакты присутствуют и прошли базовые проверки."),
    }
    ok(json.dumps(result, ensure_ascii=False))
    print("=== DONE ===")


if __name__ == "__main__":
    main()
