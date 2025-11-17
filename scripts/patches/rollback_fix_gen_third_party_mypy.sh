# scripts/patches/rollback_fix_gen_third_party_mypy.sh
set -euo pipefail
FILE="scripts/compliance/gen_third_party.py"
BAK="${FILE}.bak"

if [ ! -f "$BAK" ]; then
  echo "Backup not found: $BAK" >&2
  exit 1
fi

cp -f "$BAK" "$FILE"
echo "[OK] Rolled back $FILE from $BAK"
