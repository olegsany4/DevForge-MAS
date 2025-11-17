# scripts/patches/mypy_relax_violations_container.sh
set -euo pipefail

FILE="scripts/compliance/gen_third_party.py"
[ -f "$FILE" ] || { echo "Not found: $FILE" >&2; exit 1; }

cp -f "$FILE" "${FILE}.bak"

# 1) Если где-то объявляли общий список нарушений с жёстким типом, ослабим до list[Any]
#    Целенаправленно трогаем только строки с переменными, где встречается "violat".
perl -0777 -i -pe '
  s/(\bviolat\w*\s*:\s*)list\[\s*PyDep\s*\]/\1list[Any]/g;
  s/(\bviolat\w*\s*:\s*)list\[\s*NodeDep\s*\]/\1list[Any]/g;
  s/(\bviolat\w*\s*:\s*)list\[\s*PyDep\s*\|\s*NodeDep\s*\]/\1list[Any]/g;
' "$FILE"

# 2) Убедимся, что Any импортирован
grep -q "from typing import Any" "$FILE" || \
  sed -i '' '1,80{/from typing import/ s/$/, Any/; t;}; 1,80{/^from typing import/!{/^from __future__/!{/^import /!{h; s/.*/from typing import Any/; p; g}}}' "$FILE"

# 3) Форматирование
command -v black >/dev/null 2>&1 && black "$FILE" >/dev/null
command -v ruff  >/dev/null 2>&1 && ruff check "$FILE" --fix >/dev/null || true
command -v isort >/dev/null 2>&1 && isort "$FILE" >/dev/null

echo "[OK] mypy_relax_violations_container.sh applied to $FILE"
