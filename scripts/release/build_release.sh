#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

VERSION_FILE="$ROOT/VERSION"
VERSION="$(cat "$VERSION_FILE")"
PKG="devforge-mas-${VERSION}"
DIST_DIR="$ROOT/dist"
BUNDLE="$DIST_DIR/${PKG}.tar.gz"
SUMS="$DIST_DIR/SHA256SUMS"

echo "[INFO] Version: $VERSION"
mkdir -p "$DIST_DIR"

# 1) Предрелизная верификация
python3 tools/release_verify.py

# 2) SBOM-lite (если нет - создаем)
if [ ! -f "$ROOT/SBOM-LITE.txt" ]; then
  echo "# SBOM-LITE placeholder for ${VERSION}" > "$ROOT/SBOM-LITE.txt"
fi

# 3) Стадия сборки: создаем staging-директорию вместо GNU tar --transform
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/devforge-mas.XXXXXX")"
PKG_DIR="${STAGE}/${PKG}"
mkdir -p "$PKG_DIR"

# rsync/копирование нужных частей
rsync -a \
  --exclude ".venv" \
  --exclude "dist" \
  --exclude ".git" \
  --exclude "__pycache__" \
  VERSION CHANGELOG.md "RELEASE_NOTES_${VERSION}.md" SBOM-LITE.txt \
  compliance scripts tools db workspace src mas Makefile \
  "$PKG_DIR"

# 4) Упаковка BSD tar (без --transform)
tar -czf "$BUNDLE" -C "$STAGE" "$PKG"

# 5) Контрольные суммы
( cd "$DIST_DIR" && shasum -a 256 "$(basename "$BUNDLE")" > "$SUMS" )

# 6) Уборка
rm -rf "$STAGE"

echo "[OK] Bundle: $BUNDLE"
echo "[OK] Checksums: $SUMS"
