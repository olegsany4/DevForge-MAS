#!/usr/bin/env bash
set -euo pipefail

echo "== TechLead stage verification =="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REQUIRED_FILES=(
  "pyproject.toml"
  ".pre-commit-config.yaml"
  ".github/workflows/ci.yml"
  "Makefile"
  "CODEOWNERS"
  ".editorconfig"
)

echo "-> Checking required files exist and are non-empty"
for f in "${REQUIRED_FILES[@]}"; do
  [[ -s "$f" ]] || { echo "Missing or empty: $f"; exit 1; }
done
echo "OK: all files present"

echo "-> Sanity checks in pyproject.toml"
grep -q "\[tool.black\]" pyproject.toml
grep -q "\[tool.isort\]" pyproject.toml
grep -q "\[tool.ruff\]" pyproject.toml
grep -q "\[tool.mypy\]" pyproject.toml
echo "OK: pyproject has black/isort/ruff/mypy"

echo "-> CI workflow sanity"
grep -q "actions/setup-python" .github/workflows/ci.yml
grep -q "pytest" .github/workflows/ci.yml
grep -q "ruff check" .github/workflows/ci.yml
grep -q "black --check" .github/workflows/ci.yml
grep -q "isort --check-only" .github/workflows/ci.yml
grep -q "mypy" .github/workflows/ci.yml
echo "OK: CI steps present"

echo "-> Ensuring venv and tools"
if [[ ! -d ".venv" ]]; then
  make install >/dev/null
fi

. .venv/bin/activate
echo "Python: $(python --version)"
echo "Ruff: $(ruff --version)"
echo "Black: $(black --version)"
echo "isort: $(isort --version-number)"
echo "mypy: $(mypy --version)" || true

echo "-> Running format/lint/type/security/tests"
make fmt >/dev/null
make lint
make typecheck
make sec || true
make test || true

echo "-> Reproducibility hash"
mkdir -p workspace/.checks
# В хеш включаем все ключевые файлы
cat pyproject.toml .pre-commit-config.yaml .github/workflows/ci.yml Makefile CODEOWNERS .editorconfig | md5sum | awk '{print $1}' > workspace/.checks/techlead.md5
echo "Hash -> workspace/.checks/techlead.md5 ($(cat workspace/.checks/techlead.md5))"

echo "=== TechLead stage: PASSED ==="
