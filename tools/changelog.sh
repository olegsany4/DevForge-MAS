#!/usr/bin/env bash
set -euo pipefail

PREV_TAG="$(git describe --tags --abbrev=0 2>/dev/null || true)"
NOW_TAG="${1:-}"

if [[ -z "${NOW_TAG}" ]]; then
  echo "Usage: tools/changelog.sh vX.Y.Z" >&2
  exit 2
fi

HEADER="# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"

if [[ -z "${PREV_TAG}" ]]; then
  RANGE_ARG="--reverse --pretty=format:'- %s (%h) %ad' --date=short"
  BODY="$(git log ${RANGE_ARG})"
else
  BODY="$(git log "${PREV_TAG}..HEAD" --reverse --pretty=format:'- %s (%h) %ad' --date=short)"
fi

if [[ -z "${BODY}" ]]; then
  BODY="- Maintenance release."
fi

{
  printf "%s" "${HEADER}"
  echo "## ${NOW_TAG} — $(date +%Y-%m-%d)"
  echo
  echo "${BODY}"
  echo
} > CHANGELOG.md

echo "CHANGELOG.md generated for ${NOW_TAG}"
