#!/usr/bin/env bash
set -euo pipefail

VER="${1:?Usage: tools/release_bundle_verify.sh 0.1.0}"
BASE="workspace/release/v${VER}"

check_one() {
  local pattern="$1"
  if ! find "${BASE}" -path "${BASE}/${pattern}" -type f -print -quit | grep -q . ; then
    echo "MISSING: ${pattern}"
    return 1
  fi
}

check_one "dist/*.whl"
check_one "dist/*.tar.gz"
check_one "SHA256SUMS.txt"

echo "Bundle OK for v${VER}"
