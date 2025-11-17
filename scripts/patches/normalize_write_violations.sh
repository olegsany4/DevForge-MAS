# scripts/patches/normalize_write_violations.sh
set -euo pipefail

FILE="scripts/compliance/gen_third_party.py"
[ -f "$FILE" ] || { echo "Not found: $FILE" >&2; exit 1; }

cp -f "$FILE" "${FILE}.bak"

# 1) Удалим предыдущие версии функций _write_violations / _write_violations_legacy (если были)
#    Режим по диапазону: от "def _write_violations" до следующего "def " или конца файла.
perl -0777 -i -pe '
  s/\n(def\s+_write_violations_legacy\b[\s\S]*?)(?=\n\w*def\s|\Z)//g;
  s/\n(def\s+_write_violations\b[\s\S]*?)(?=\n\w*def\s|\Z)//g;
' "$FILE"

# 2) Вставим fallback для _license_policy_ok, если нет
grep -q "_license_policy_ok" "$FILE" || cat >> "$FILE" <<'PYCODE'

# --- SAFE FALLBACK: _license_policy_ok (если отсутствует) ---
def _license_policy_ok(lic: str) -> bool:  # noqa: D401
    """Policy gate: базовая проверка лицензии согласно локальной политике."""
    ALLOWED = {
        "MIT","BSD","BSD-2-Clause","BSD-3-Clause","Apache-2.0","MPL-2.0","LGPL-2.1","LGPL-3.0",
        # часто встречающееся добро:
        "ISC","Unicode-DFS-2016","Python-2.0","Zlib","OpenSSL",
    }
    DISALLOWED = {"GPL","GPL-2.0","GPL-3.0","AGPL","AGPL-3.0"}
    if lic in ALLOWED:
        return True
    if lic in DISALLOWED or lic == "UNKNOWN" or not lic:
        return False
    return False
# --- END FALLBACK ---
PYCODE

# 3) Вставим fallback для VIOLATIONS_JSON, если нет
grep -q "VIOLATIONS_JSON" "$FILE" || cat >> "$FILE" <<'PYCODE'

# --- SAFE FALLBACK: путь вывода нарушений ---
try:
    VIOLATIONS_JSON  # type: ignore[name-defined]
except Exception:
    from pathlib import Path as _Path
    OUT_BASE = OUT_MD.parent if "OUT_MD" in globals() else _Path("compliance")  # type: ignore[name-defined]
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    VIOLATIONS_JSON = OUT_BASE / "_violations.json"  # type: ignore[assignment]
# --- END FALLBACK ---
PYCODE

# 4) Добавим «чистую» реализацию _write_violations (без смешения типов)
cat >> "$FILE" <<'PYCODE'

# --- SAFE REFACTOR: mypy-proof writer ---
from typing import Any as _Any

def _write_violations(
    py_deps: "Iterable[PyDep]",
    node_deps: "Iterable[NodeDep]",
    policy: dict[str, object] | None = None,
) -> None:
    """
    Пишем нарушения как list[dict[str,str]] — не смешиваем PyDep/NodeDep в одном list[T].
    Не ломает API: точка вызова и файл-назначение остаются прежними.
    """
    items: list[dict[str, str]] = []

    # Разбор политики (гибко: поддерживаем str / list / set)
    allowed_extra: set[str] = set()
    ignore_raw: set[str] = set()
    if isinstance(policy, dict):
        ax = policy.get("allowed_extra")
        ig = policy.get("ignore")
        if isinstance(ax, (list, set, tuple)):  # noqa: UP038
            allowed_extra = {str(x).strip() for x in ax if str(x).strip()}
        elif isinstance(ax, str):
            allowed_extra = {s.strip() for s in ax.split(",") if s.strip()}
        if isinstance(ig, (list, set, tuple)):  # noqa: UP038
            ignore_raw = {str(x).strip() for x in ig if str(x).strip()}
        elif isinstance(ig, str):
            ignore_raw = {s.strip() for s in ig.split(",") if s.strip()}

    def _ignored(name: str, version: str) -> bool:
        if not ignore_raw:
            return False
        full = f"{name}@{version}" if version else name
        return (full in ignore_raw) or (name in ignore_raw)

    def _policy_ok_ext(name: str, version: str, lic: str) -> bool:
        ok = _license_policy_ok(lic)
        if lic in allowed_extra:
            ok = True
        if _ignored(name, version):
            ok = True
        return ok

    for d in py_deps:
        lic = getattr(d, "license", "")
        name = getattr(d, "name", "")
        version = getattr(d, "version", "") or ""
        if not _policy_ok_ext(name, version, lic):
            items.append({"eco": "python", "name": name, "version": version, "license": lic})

    for d in node_deps:
        lic = getattr(d, "license", "")
        name = getattr(d, "name", "")
        version = getattr(d, "version", "") or ""
        if not _policy_ok_ext(name, version, lic):
            items.append({"eco": "node", "name": name, "version": version, "license": lic})

    VIOLATIONS_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")  # type: ignore[name-defined]
# --- END SAFE REFACTOR ---
PYCODE

# 5) Форматирование
command -v black >/dev/null 2>&1 && black "$FILE" >/dev/null
command -v ruff  >/dev/null 2>&1 && ruff check "$FILE" --fix >/dev/null || true
command -v isort >/dev/null 2>&1 && isort "$FILE" >/dev/null

echo "[OK] normalize_write_violations.sh applied to $FILE"
