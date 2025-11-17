#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADR_IDX="$ROOT_DIR/workspace/adr/ADR-INDEX.md"
ADR_SET="$ROOT_DIR/workspace/adr/ADR-SET.json"
LAYOUT="$ROOT_DIR/workspace/layout/LAYOUT.json"
CONTRACTS="$ROOT_DIR/src/devforge_mas/schemas/CONTRACTS.json"
CHECKSUM_DIR="$ROOT_DIR/workspace/.checks"
CHECKSUM_FILE="$CHECKSUM_DIR/architect.md5"

# 1) Наличие файлов
for f in "$ADR_IDX" "$ADR_SET" "$LAYOUT" "$CONTRACTS"; do
  [[ -s "$f" ]] || { echo "FAIL: missing or empty $f"; exit 1; }
done
echo "OK: required files exist and are non-empty"

# 2) Валидность JSON
for jf in "$ADR_SET" "$LAYOUT" "$CONTRACTS"; do
  jq -e . "$jf" >/dev/null
done
echo "OK: JSON files are well-formed"

# 3) Ограничение ADR ≤ 10
ADR_COUNT="$(jq '.adr | length' "$ADR_SET")"
if [[ "$ADR_COUNT" -le 10 && "$ADR_COUNT" -ge 1 ]]; then
  echo "OK: ADR count = $ADR_COUNT"
else
  echo "FAIL: ADR count must be 1..10 (got $ADR_COUNT)"; exit 1;
fi

# 4) Минимальные ключи контрактов
jq -e '
  .contracts.api.service and
  .contracts.api.version and
  .contracts.endpoints and
  (.contracts.endpoints | length >= 3) and
  .contracts.schemas.Brief and
  .contracts.schemas.AcceptanceCriteria and
  .contracts.schemas.AgentResult
' "$CONTRACTS" >/dev/null || { echo "FAIL: CONTRACTS.json missing required keys"; exit 1; }
echo "OK: CONTRACTS.json has required keys"

# 5) Крастест эндпоинтов: методы/пути
jq -e '
  .contracts.endpoints
  | all( (.method | IN("GET","POST","PUT","DELETE")) and (.path | startswith("/")) )
' "$CONTRACTS" >/dev/null || { echo "FAIL: endpoints methods/paths invalid"; exit 1; }
echo "OK: endpoints methods/paths sane"

# 6) Контроль воспроизводимости (хеш-срез)
mkdir -p "$CHECKSUM_DIR"
cat "$ADR_IDX" "$ADR_SET" "$LAYOUT" "$CONTRACTS" | md5sum | awk '{print $1}' > "$CHECKSUM_FILE"
echo "OK: reproducibility hash -> $CHECKSUM_FILE"

# 7) Быстрая структурная проверка на Python
python3 "$ROOT_DIR/tools/validate_contracts.py" --fast

echo "=== Architect stage: PASSED ==="
