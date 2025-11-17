# scripts/patches/fix_gen_third_party_mypy.sh
set -euo pipefail

FILE="scripts/compliance/gen_third_party.py"

if [ ! -f "$FILE" ]; then
  echo "Not found: $FILE" >&2
  exit 1
fi

# 1) Бэкап
cp -f "$FILE" "${FILE}.bak"

# 2) Переименовать старую функцию, чтобы не трогать вызовы (они будут указывать на новую)
#    Идём по имени сигнатуры и меняем только объявление.
perl -0777 -i -pe 's/\bdef\s+_write_violations\b/def _write_violations_legacy/g' "$FILE"

# 3) Добавить новую реализацию в конец файла
cat >> "$FILE" <<'PYCODE'

# --- SAFE REFACTOR APPEND: mypy-proof violations writer ---
def _write_violations(
    py_deps: Iterable[PyDep],
    node_deps: Iterable[NodeDep],
    policy: dict[str, object] | None = None,
) -> None:
    """
    Записывает нарушения политики в JSON-формате как список словарей.
    Важно: не складывает PyDep/NodeDep в общий типизированный список (иначе mypy падает),
    поэтому используем list[dict[str, str]].
    """
    items: list[dict[str, str]] = []

    # Опциональная политика (если есть лоадер политики в проекте)
    allowed_extra: set[str] = set()
    ignore_raw: set[str] = set()
    if policy:
        # допускаем разные ключи, чтобы быть backward-compatible
        ax = policy.get("allowed_extra") if isinstance(policy, dict) else None
        ig = policy.get("ignore") if isinstance(policy, dict) else None
        # поддержим варианты строк/списков/сет
        if ax:
            if isinstance(ax, (list, set, tuple)):
                allowed_extra = {str(x).strip() for x in ax if str(x).strip()}
            elif isinstance(ax, str):
                allowed_extra = {s.strip() for s in ax.split(",") if s.strip()}
        if ig:
            if isinstance(ig, (list, set, tuple)):
                ignore_raw = {str(x).strip() for x in ig if str(x).strip()}
            elif isinstance(ig, str):
                ignore_raw = {s.strip() for s in ig.split(",") if s.strip()}

    def _ignored(name: str, version: str) -> bool:
        if not ignore_raw:
            return False
        full = f"{name}@{version}" if version else name
        return (full in ignore_raw) or (name in ignore_raw)

    def _policy_ok_ext(name: str, version: str, lic: str) -> bool:
        # базовая проверка
        ok = _license_policy_ok(lic)
        # доп. разрешённые лицензии из политики
        if lic in allowed_extra:
            ok = True
        # пакет в ignore: считаем ок
        if _ignored(name, version):
            ok = True
        return ok

    # Python deps
    for d in py_deps:
        lic = d.license
        if not _policy_ok_ext(d.name, d.version, lic):
            items.append({"eco": "python", "name": d.name, "version": d.version or "", "license": lic})

    # Node deps
    for d in node_deps:
        lic = d.license
        if not _policy_ok_ext(d.name, d.version, lic):
            items.append({"eco": "node", "name": d.name, "version": d.version or "", "license": lic})

    # Путь к JSON с нарушениями должен быть определён в модуле (как в твоей версии)
    try:
        VIOLATIONS_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")  # type: ignore[name-defined]
    except NameError:
        # Fallback: если переменной нет — пишем рядом с OUT_MD
        out_base = OUT_MD.parent if 'OUT_MD' in globals() else Path("compliance")  # type: ignore[name-defined]
        out_base.mkdir(parents=True, exist_ok=True)
        (out_base / "_violations.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
# --- END SAFE REFACTOR APPEND ---
PYCODE

# 4) Форматирование (если окружение активно)
if command -v black >/dev/null 2>&1; then
  black "$FILE" >/dev/null
fi
if command -v ruff >/dev/null 2>&1; then
  ruff check "$FILE" --fix >/dev/null || true
fi
if command -v isort >/dev/null 2>&1; then
  isort "$FILE" >/dev/null
fi

echo "[OK] Patched $FILE (legacy kept at _write_violations_legacy, new _write_violations added)"
