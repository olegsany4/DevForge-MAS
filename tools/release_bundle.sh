#!/usr/bin/env bash
set -euo pipefail
VER="${1:?Usage: tools/release_bundle.sh 0.1.0}"

ROOT="$(git rev-parse --show-toplevel)"
OUT_DIR="${ROOT}/workspace/release/v${VER}"
ZIP_NAME="devforge-mas-v${VER}.zip"

mkdir -p "${OUT_DIR}"

# Копируем основные артефакты
cp -f CHANGELOG.md "${OUT_DIR}/" || true
cp -f README.md    "${OUT_DIR}/" || true
cp -f LICENSE*     "${OUT_DIR}/" || true
mkdir -p "${OUT_DIR}/dist"
cp -f dist/* "${OUT_DIR}/dist/"

# Кладём compliance-артефакты, если есть
if [[ -d "${ROOT}/compliance" ]]; then
  mkdir -p "${OUT_DIR}/compliance"
  for f in NOTICE OBLIGATIONS.md THIRD_PARTY_LICENSES.md; do
    [[ -f "${ROOT}/compliance/${f}" ]] && cp -f "${ROOT}/compliance/${f}" "${OUT_DIR}/compliance/"
  done
fi

# Подписи (sha256)
(
  cd "${OUT_DIR}"
  # macOS: shasum
  find . -type f ! -name "${ZIP_NAME}" -print0 | xargs -0 shasum -a 256 > SHA256SUMS.txt
)

# ZIP-архив бандла
(
  cd "$(dirname "${OUT_DIR}")"
  rm -f "${ZIP_NAME}"
  zip -r "${ZIP_NAME}" "v${VER}" >/dev/null
)

echo "Release bundle created:"
echo " - ${OUT_DIR}"
echo " - $(dirname "${OUT_DIR}")/${ZIP_NAME}"
