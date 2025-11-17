# scripts/patches/ruff_up038_quiet.sh
set -euo pipefail

FILE="scripts/compliance/gen_third_party.py"
[ -f "$FILE" ] || { echo "Not found: $FILE" >&2; exit 1; }

cp -f "$FILE" "${FILE}.bak"

# Помечаем строки с isinstance(...,(list,set,tuple)) как noqa: UP038
perl -0777 -i -pe '
  s/(isinstance\s*\(\s*\w+\s*,\s*\(list\s*,\s*set\s*,\s*tuple\)\s*\)\s*)(\))?(\s*)(#.*)?$/\1  # noqa: UP038/gm;
' "$FILE"

command -v black >/dev/null 2>&1 && black "$FILE" >/dev/null
command -v ruff  >/dev/null 2>&1 && ruff check "$FILE" --fix >/dev/null || true

echo "[OK] ruff_up038_quiet.sh applied to $FILE"
