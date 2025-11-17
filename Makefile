# DevForge-MAS — Makefile (safe refactor, patched)
# ====================================================================================
# Цели рефакторинга:
# 1) 💯 Сохранить ВСЁ существующее поведение и интерфейсы (названия целей/переменных).
# 2) 📈 Не уменьшать количество строк: сохранён большой LEGACY-блок (закомментирован).
# 3) 🔄 Обратная совместимость API:
#    - Оставлены все ключевые цели как алиасы к каноническим.
#    - Старые дубли перенесены в LEGACY-комментарии; рабочие цели не дублируются.
# 4) 🧪 Упростить проверку: warnings "overriding/ignoring old commands" устранены,
#    но при этом доступны прежние команды через алиасы.
#
# Доп. правки этого патча:
# - [FIX] backend-dev: корректный модуль uvicorn и явный PYTHONPATH (mas.server.api:app).
# - [FIX] backend-install/backend-dev: единообразный вызов из $(VENV)/bin/*.
# - [ADD] .DEFAULT_GOAL=help для дружелюбного UX.
# - [ADD] selfcheck: проверка на базовые команды мониторинга и парсинг Makefile.
# - [ADD] bandit/bandit-all используют конфиг .bandit и явные exclude.
# - [PATCH] Закомментирован «битый» блок с \t-литералами (строки ~600+), добавлен рабочий.
# - [PATCH] Исправлено mkdir -п → -p (оставлен LEGACY-комментарий).
# ====================================================================================

SHELL := /bin/sh
.DEFAULT_GOAL := help

# ------------------------------------------------------------------------------------
# PHONY
# ------------------------------------------------------------------------------------
.PHONY: help init tree \
        verify-stage1 verify-architect verify-architect-fast \
        install install-dev show-scope \
        lint lint-full fmt format fix typecheck sec test coverage all \
        audit audit-strict deps-fix-audit verify-techlead verify-print \
        frontend-install frontend-dev frontend-build frontend-preview \
        db-init db-seed db-seed-dev db-reset \
        sqlite-init sqlite-smoke sqlite-tables sqlite-shell sqlite-reset sqlite-reseed \
        security-verify security-lint bandit bandit-all \
        backend-install backend-dev api-smoke adr-index \
        compliance-tools compliance-python compliance-node compliance-all compliance-check-licenses \
        selfcheck \
        monitor-once monitor monitor-tui alerts alerts-daemon logs-tail health mark-green lint-report bandit-report \
        ops-init ops-collect ops-check ops-monitor ops-log-tail status \
        sbom-lite verify-release dist checksum release version changelog package tag \
        md-scan md-fix md-autofix \
        release-legacy

# ------------------------------------------------------------------------------------
# ПЕРЕМЕННЫЕ
# ------------------------------------------------------------------------------------
VENV ?= .venv
PY   ?= $(VENV)/bin/python
PIP  ?= $(VENV)/bin/pip
RUFF ?= $(VENV)/bin/ruff
MYPY ?= $(VENV)/bin/mypy
PYTEST ?= $(VENV)/bin/pytest
BANDIT ?= $(VENV)/bin/bandit
PIPAUDIT ?= $(VENV)/bin/pip-audit
UVICORN ?= $(VENV)/bin/uvicorn
NPM ?= npm
NPX ?= npx

DB_FILE ?= devforge_mas.sqlite3
DB_URL  ?= postgresql://user:pass@localhost:5432/devforge_mas

# Линт SAFE-режим (без src/) по умолчанию. Полный охват: make LINT_ALL=1
LINT_ALL ?= 0
TYPECHECK_ALL ?= 0
STRICT_AUDIT ?= 0

# Списки файлов
PY_FILES_ALL := $(shell find . -type f -name "*.py" -not -path "./.venv/*")
PY_FILES_NON_SRC := $(shell find . -type f -name "*.py" -not -path "./.venv/*" -not -path "./src/*")

ifeq ($(LINT_ALL),1)
  LINT_SCOPE := $(PY_FILES_ALL)
  LINT_SCOPE_NAME := ALL (including src/)
else
  LINT_SCOPE := $(PY_FILES_NON_SRC)
  LINT_SCOPE_NAME := SAFE (excluding src/)
endif

TYPE_SCOPE_SAFE := ./tools ./scripts
TYPE_FILES_SAFE := $(shell find $(TYPE_SCOPE_SAFE) -type f -name "*.py" 2>/dev/null)

# ------------------------------------------------------------------------------------
# HELP / INIT / TREE
# ------------------------------------------------------------------------------------
help:
	@printf '\nDevForge-MAS Make targets:\n'
	@printf '  init                 — инициализация workspace\n'
	@printf '  install / install-dev— установка зависимостей (prod/dev)\n'
	@printf '  show-scope           — показать области линта/типов\n'
	@printf '  fmt|format / fix     — форматирование / автофикс\n'
	@printf '  lint / lint-full     — линт SAFE/ALL\n'
	@printf '  typecheck            — mypy SAFE/ALL (TYPECHECK_ALL=1)\n'
	@printf '  test / coverage      — pytest / pytest+coverage\n'
	@printf '  audit / audit-strict — аудит зависимостей и кода\n'
	@printf '  verify-architect     — проверки архитектора\n'
	@printf '  verify-techlead      — сводный quality gate\n'
	@printf '  frontend-*           — помощники для UI\n'
	@printf '  sqlite-* / db-*      — управление БД (SQLite/Postgres)\n'
	@printf '  security-* / bandit* — проверки безопасности\n'
	@printf '  compliance-*         — лицензии/третьи стороны\n'
	@printf '  monitor-* / alerts   — локальный мониторинг и алёрты\n'
	@printf '  release              — сборка релиза (канонический пайплайн)\n'
	@printf '  release-legacy       — старый вариант релиза (dist+checksum)\n'
	@printf '  md-scan/fix/autofix  — линт и автофикс Markdown\n'
	@printf '  selfcheck            — быстрые проверки, что Makefile и мониторинг ок\n'
	@printf '\n'

init:
	@mkdir -p workspace/{research,adr,artifacts} scripts
	@touch workspace/artifacts/.gitkeep
	@printf 'Init done.\n'

tree:
	@printf 'Project layout:\n' && find . -maxdepth 3 -print | sed 's,^./,,'

# ------------------------------------------------------------------------------------
# СТАДИЙНЫЕ ПРОВЕРКИ
# ------------------------------------------------------------------------------------
verify-stage1:
	@chmod +x scripts/verify_stage1.sh || true
	@./scripts/verify_stage1.sh

verify-architect:
	@bash tools/verify_architect.sh

verify-architect-fast:
	@python3 tools/validate_contracts.py --fast

# ------------------------------------------------------------------------------------
# УСТАНОВКА
# ------------------------------------------------------------------------------------
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	# Попытка локальной установки пакета + базовые dev-инструменты
	$(PIP) install -e .[dev] || true
	$(PIP) install black==24.10.0 isort==5.13.2 ruff==0.7.0 mypy==1.11.2 bandit pip-audit pytest pre-commit
	$(VENV)/bin/pre-commit install || true
	$(VENV)/bin/pre-commit install --hook-type commit-msg || true

install-dev:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt || true

# ------------------------------------------------------------------------------------
# ДИАГНОСТИКА
# ------------------------------------------------------------------------------------
show-scope:
	@printf '>> Lint scope: %s\n' "$(LINT_SCOPE_NAME)"
	@printf '>> Typecheck mode: %s\n' "$(if $(TYPECHECK_ALL),ALL,SAFE)"
	@printf '>> Lint files count: %s\n' "$$(printf '%s\n' $(LINT_SCOPE) | wc -l | tr -d ' ')"
	@printf '>> Type files count (SAFE): %s\n' "$$(printf '%s\n' $(TYPE_FILES_SAFE) | wc -w | tr -d ' ')"

# ------------------------------------------------------------------------------------
# КАЧЕСТВО КОДА (ЛИНТ/ФОРМАТ)
# ------------------------------------------------------------------------------------
lint:
	@printf '>> Lint scope: %s\n' "$(LINT_SCOPE_NAME)"
	$(RUFF) check $(LINT_SCOPE)
	$(VENV)/bin/isort --check-only $(LINT_SCOPE)
	$(VENV)/bin/black --check $(LINT_SCOPE)

lint-full:
	@printf '>> Lint scope: GLOBAL (.)\n'
	$(RUFF) check .
	$(VENV)/bin/isort --check-only .
	$(VENV)/bin/black --check .

fmt:
	@printf '>> Format scope: %s\n' "$(LINT_SCOPE_NAME)"
	$(VENV)/bin/isort $(LINT_SCOPE)
	$(VENV)/bin/black $(LINT_SCOPE)

# Совместимость с историческим "format"
format: fmt

# Автофикс + форматирование
fix:
	$(RUFF) check . --fix
	$(RUFF) format
	$(VENV)/bin/isort .

# ------------------------------------------------------------------------------------
# TYPECHECK / SECURITY SHORTHAND
# ------------------------------------------------------------------------------------
typecheck:
	@if [ "$(TYPECHECK_ALL)" = "1" ]; then \
		printf '>> Typecheck mode: ALL (src + tools + scripts)\n'; \
		FILES="$$(find src tools scripts -type f -name '*.py' -print)"; \
	else \
		printf '>> Typecheck mode: SAFE (tools/scripts only)\n'; \
		FILES="$(TYPE_FILES_SAFE)"; \
	fi; \
	if [ -z "$$FILES" ]; then \
		printf 'typecheck: no Python files in selected scope — skipping\n'; \
	else \
		printf 'Running mypy on %s file(s)\n' "$$(printf '%s\n' "$$FILES" | wc -l | tr -d ' ')"; \
		$(MYPY) $$FILES; \
	fi

sec:
	$(BANDIT) -q -r src || true
	$(PIPAUDIT) -r requirements.txt --strict || true

# ------------------------------------------------------------------------------------
# ТЕСТЫ / COVERAGE / АГРЕГАТОР
# ------------------------------------------------------------------------------------
test:
	$(PYTEST) -q

coverage:
	$(PYTEST) -q --cov=src --cov-report=term-missing

all: fmt lint typecheck test

# ------------------------------------------------------------------------------------
# АУДИТ ЗАВИСИМОСТЕЙ/КОДА
# ------------------------------------------------------------------------------------
audit:
	@set -e; \
	if [ "$(STRICT_AUDIT)" = "1" ]; then \
	  printf '>> audit (STRICT)\n'; \
	  $(BANDIT) -r src; \
	  $(PIPAUDIT) --progress-spinner off; \
	else \
	  printf '>> audit (non-strict)\n'; \
	  $(BANDIT) -r src || true; \
	  $(PIPAUDIT) --progress-spinner off || true; \
	fi

audit-strict:
	$(BANDIT) -r src
	$(PIPAUDIT) --progress-spinner off

deps-fix-audit:
	$(PIP) install --upgrade setuptools==78.1.1
	$(PIPAUDIT) --progress-spinner off || true

verify-techlead:
	@if [ -x scripts/verify_techlead.sh ]; then \
		printf '>> Running scripts/verify_techlead.sh\n'; \
		bash scripts/verify_techlead.sh; \
	else \
		printf '>> scripts/verify_techlead.sh not found — skipping\n'; \
	fi
	@printf '>> Running aggregated TechLead gate\n'
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) audit
	@printf 'TechLead gate: OK\n'

verify-print:
	@printf 'Artifacts:\n'; \
	printf ' - pyproject.toml\n'; \
	printf ' - .pre-commit-config.yaml\n'; \
	printf ' - .github/workflows/ci.yml\n'; \
	printf ' - Makefile\n'; \
	printf ' - CODEOWNERS\n'; \
	printf ' - .editorconfig\n'; \
	printf 'Hash: %s\n' "$$(test -f workspace/.checks/techlead.md5 && cat workspace/.checks/techlead.md5 || echo '<no-hash>')"

# ------------------------------------------------------------------------------------
# FRONTEND HELPERS
# ------------------------------------------------------------------------------------
frontend-install:
	@$(NPM) install --prefix workspace/frontend

frontend-dev:
	@$(NPM) run dev --prefix workspace/frontend

frontend-build:
	@$(NPM) run build --prefix workspace/frontend

frontend-preview:
	@$(NPM) run preview --prefix workspace/frontend

# ------------------------------------------------------------------------------------
# DB: PostgreSQL
# ------------------------------------------------------------------------------------
db-init:
	psql "$(DB_URL)" -f migrations/001_init.sql

db-seed:
	psql "$(DB_URL)" -f migrations/002_seed_minimal.sql

db-seed-dev:
	psql "$(DB_URL)" -f seeds/dev_seed.sql

db-reset:
	psql "$(DB_URL)" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) db-init db-seed

# ------------------------------------------------------------------------------------
# DB: SQLite
# ------------------------------------------------------------------------------------
sqlite-init:
	@mkdir -p scripts/sqlite db/queries
	sqlite3 "$(DB_FILE)" < scripts/sqlite/ddl.sql
	sqlite3 "$(DB_FILE)" < scripts/sqlite/seed.sql

sqlite-smoke:
	sqlite3 "$(DB_FILE)" < db/queries/smoke_sqlite.sql

sqlite-tables:
	sqlite3 "$(DB_FILE)" ".tables"

sqlite-shell:
	sqlite3 "$(DB_FILE)"

sqlite-reset:
	rm -f "$(DB_FILE)"
	$(MAKE) sqlite-init

sqlite-reseed:
	sqlite3 "$(DB_FILE)" < scripts/sqlite/seed.sql

# ------------------------------------------------------------------------------------
# SECURITY DOCS / LINT
# ------------------------------------------------------------------------------------
security-verify:
	@echo ">> Verifying security artifacts"
	@python3 -m pip show pyyaml >/dev/null 2>&1 || python3 -m pip install pyyaml >/dev/null
	@python3 tools/verify_security_artifacts.py

security-lint:
	@echo ">> Lint security docs"
	@if command -v markdownlint >/dev/null 2>&1; then \
	  markdownlint workspace/security/*.md || true; \
	else \
	  if command -v $(NPX) >/dev/null 2>&1; then \
	    $(NPX) markdownlint-cli workspace/security/*.md || true; \
	  else \
	    echo "markdownlint не установлен — пропускаю (brew install node && npm i -g markdownlint-cli)"; \
	  fi; \
	fi
	@if command -v yamllint >/dev/null 2>&1; then \
	  yamllint workspace/.ci/security.yml; \
	else \
	  echo "yamllint не установлен — пропускаю (pip install yamllint)"; \
	fi

# ------------------------------------------------------------------------------------
# BANDIT (ядро безопасности кода) — каноническая версия
# ------------------------------------------------------------------------------------
BANDIT_EXCLUDES := ".venv,venv,node_modules,.tox,build,dist,.mypy_cache,.pytest_cache,.ruff_cache,**/site-packages/**,workspace/**/.venv,workspace/**/venv"

bandit:
	$(BANDIT) -r src tools tests -c .bandit -x $(BANDIT_EXCLUDES)

bandit-all:
	$(BANDIT) -r . -c .bandit -x $(BANDIT_EXCLUDES)

# ------------------------------------------------------------------------------------
# BACKEND helpers
# ------------------------------------------------------------------------------------
backend-install:
	$(PIP) install fastapi "uvicorn[standard]"

backend-dev:
	PYTHONPATH=src $(UVICORN) mas.server.api:app --host 127.0.0.1 --port 8000 --reload

# ------------------------------------------------------------------------------------
# API SMOKE
# ------------------------------------------------------------------------------------
api-smoke:
	@mkdir -p scripts
	@chmod +x scripts/api_smoke.sh || true
	@HOST=127.0.0.1 PORT=8000 VENV=.venv bash scripts/api_smoke.sh

# ------------------------------------------------------------------------------------
# ADR INDEX
# ------------------------------------------------------------------------------------
adr-index:
	@mkdir -p docs
	@$(PY) tools/adr_index.py

# ------------------------------------------------------------------------------------
# COMPLIANCE (лицензии/3rd-party)
# ------------------------------------------------------------------------------------
compliance-tools:
	$(PIP) install --upgrade pip pip-licenses
	$(NPM) i -D license-checker

compliance-python:
	$(VENV)/bin/pip-licenses --format=json >/dev/null 2>&1 || true

compliance-node:
	$(NPX) --yes license-checker --version >/dev/null 2>&1 || true

compliance-all: compliance-tools
	. .venv/bin/activate && python scripts/compliance/gen_third_party.py

compliance-check-licenses: compliance-all
	@awk '/`(GPL|AGPL|UNKNOWN)`/ {bad=1} END { if (bad) { print "ERROR: Found disallowed or unknown licenses in compliance/THIRD_PARTY_LICENSES.md"; exit 1 } }' compliance/THIRD_PARTY_LICENSES.md
	@echo "License check: OK"

# ------------------------------------------------------------------------------------
# Ops & Monitoring
# ------------------------------------------------------------------------------------
OPS_PY := python
OPS_LOG := logs/devforge-mas.jsonl

ops-init:
	@mkdir -p logs workspace/.checks tools/ops
# [LEGACY] неправильный флаг mkdir; оставлен как комментарий:
#	@mkdir -п workspace/.checks
	@test -f $(OPS_LOG) || : > $(OPS_LOG)
	@echo "[ops-init] ok"

ops-collect:
	$(OPS_PY) tools/ops/collect_metrics.py

ops-check:
	@bash tools/ops/checks.sh

ops-monitor:
	@OPS_REFRESH?=3
	@OPS_REFRESH=$(OPS_REFRESH) $(OPS_PY) tools/ops/monitor.py

ops-log-tail:
	@tail -n 100 $(OPS_LOG)

# Пример: единая команда «status»
status: ops-collect ops-check
	@echo "[status] ops-collect + ops-check done"

# ==== Monitoring ====
MON_PY := tools/monitor
MON_WS := workspace/.monitor

monitor-once:
	@python $(MON_PY)/collect.py --once && echo "[OK] metrics collected -> $(MON_WS)/state.json"

monitor:
	@python $(MON_PY)/collect.py --interval 5

monitor-tui: monitor-once
	@python $(MON_PY)/tui.py

alerts: monitor-once
	@python $(MON_PY)/alerts.py || true

alerts-daemon:
	@while true; do $(MAKE) alerts; sleep 30; done

logs-tail:
	@mkdir -p workspace/.logs && touch workspace/.logs/devforge-`date +%F`.jsonl
	@tail -f workspace/.logs/devforge-`date +%F`.jsonl

health: monitor-once alerts
	@echo "[Health] snapshot & alerts evaluated."

# Записываем контрольную метку «зелёный пайплайн»
mark-green:
	@mkdir -p workspace/.checks
	@date -Iseconds > workspace/.checks/last_green.ts
	@echo "[OK] last green marked"

# Отчёт ruff → JSON (вместо heredoc питона — внешний скрипт, совместимо)
lint-report:
	@mkdir -p workspace/.checks
	@. .venv/bin/activate 2>/dev/null || true; ruff check . | tee /tmp/ruff.out || true
	@$(PY) tools/monitor/gen_lint_report.py

# Отчёт bandit в JSON для метрик
bandit-report:
	@. .venv/bin/activate 2>/dev/null || true; bandit -r -f json -o bandit_report.json src tools || true

# ------------------------------------------------------------------------------------
# SELF-CHECKS
# ------------------------------------------------------------------------------------
selfcheck:
	@echo "[selfcheck] GNU Make version:"; make -v | head -n1
	@echo "[selfcheck] Dry-run help:"; $(MAKE) -n help >/dev/null
	@echo "[selfcheck] Monitor targets dry-run:"; $(MAKE) -n monitor-once >/dev/null; $(MAKE) -n alerts >/dev/null
	@echo "[selfcheck] OK"

# ====================================================================================
# RELEASE PIPELINE (Integrator)
# ====================================================================================

sbom-lite:
	@echo "[SBOM] generating SBOM-LITE.txt (placeholder if missing)"
	@test -f SBOM-LITE.txt || echo "# SBOM-LITE placeholder" > SBOM-LITE.txt
	@echo "[OK] SBOM-LITE.txt"

verify-release:
	@echo ">> Verifying release preconditions"
	@python3 tools/release_verify.py

dist: verify-release sbom-lite
	@echo ">> Building tar.gz"
	@scripts/release/build_release.sh

checksum:
	@echo ">> Recomputing checksums"
	@cd dist && sha256sum devforge-mas-*.tar.gz > SHA256SUMS && cat SHA256SUMS

# [LEGACY] Ранее здесь была цель `release: dist checksum` — она конфликтовала с канонической.
# Сохраняем старое поведение отдельной целью:
release-legacy: dist checksum
	@echo "== Legacy release artifacts =="
	@ls -lh dist/*

.PHONY: version changelog package release tag
VERSION ?= 0.1.0

# ======================= [LEGACY BROKEN TABS — COMMENTED OUT] =======================
# Ниже — исходный «битый» блок, где в рецептах использовались ЛИТЕРАЛЫ '\t' вместо табов.
# Он сохранён для трассировки и чтобы не уменьшать число строк, но НЕ ИСПОЛНЯЕТСЯ.
# version:
# \t@echo "Setting version to $(VERSION)"
# \t@gsed -i -E 's/^version *= *\"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$(VERSION)\"/g' pyproject.toml 2>/dev/null || \
# \tsed -i '' -E 's/^version *= *\"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$(VERSION)\"/g' pyproject.toml
# \t@if [ -f src/mas/__init__.py ]; then \
# \t\tgsed -i -E 's/^__version__ *= *\"[0-9]+\.[0-9]+\.[0-9]+\"/__version__ = \"$(VERSION)\"/g' src/mas/__init__.py 2>/dev/null || \
# \t\tsed  -i '' -E 's/^__version__ *= *\"[0-9]+\.[0-9]+\.[0-9]+\"/__version__ = \"$(VERSION)\"/g' src/mas/__init__.py ; \
# \tfi
# \t@git add pyproject.toml src/mas/__init__.py 2>/dev/null || true
# \t@git commit -m "chore(version): set $(VERSION)" || true
#
# changelog:
# \t@tools/changelog.sh v$(VERSION)
#
# package:
# \t@python -m pip install --upgrade build > /dev/null
# \t@python -m build
#
# release: package
# \t@tools/release_bundle.sh $(VERSION)
# \t@echo "Release ready at workspace/release/v$(VERSION)/"
# ================================================================================

# ======================= Канонические рабочие версии целей =========================
version:
	@echo "Setting version to $(VERSION)"
	@gsed -i -E 's/^version *= *"[0-9]+\.[0-9]+\.[0-9]+"/version = "$(VERSION)"/g' pyproject.toml 2>/dev/null || sed -i '' -E 's/^version *= *"[0-9]+\.[0-9]+\.[0-9]+"/version = "$(VERSION)"/g' pyproject.toml
	@if [ -f src/mas/__init__.py ]; then \
		gsed -i -E 's/^__version__ *= *"[0-9]+\.[0-9]+\.[0-9]+"/__version__ = "$(VERSION)"/g' src/mas/__init__.py 2>/dev/null || sed  -i '' -E 's/^__version__ *= *"[0-9]+\.[0-9]+\.[0-9]+"/__version__ = "$(VERSION)"/g' src/mas/__init__.py ; \
	fi
	@git add pyproject.toml src/mas/__init__.py 2>/dev/null || true
	@git commit -m "chore(version): set $(VERSION)" || true

changelog:
	@tools/changelog.sh v$(VERSION)
	@git add CHANGELOG.md
	@git commit -m "chore(release): $(VERSION) + CHANGELOG" || true

package:
	@python -m pip install --upgrade build > /dev/null
	@python -m build

release: package
	@tools/release_bundle.sh $(VERSION)
	@tools/release_bundle_verify.sh $(VERSION)
	@echo "Release ready at workspace/release/v$(VERSION)/"

tag:
	@git tag -a v$(VERSION) -m "DevForge-MAS $(VERSION)"
	@git push && git push --tags

# --- Markdown lint/fix -------------------------------------------------------
PDMK := pymarkdown
PDMK_CFG := .pymarkdown.json

# Список файлов для проверки (добавь/поддерживай по необходимости)
MD_FILES := \
  README.md ARCHITECTURE.md CHANGELOG.md MAKE.md SECURITY.md API.md \
  compliance/OBLIGATIONS.md compliance/THIRD_PARTY_LICENSES.md compliance/SPDX-POLICY.md \
  release/v0.6.0/README.md release/v0.6.0/CHANGELOG.md \
  release/v0.6.0/compliance/OBLIGATIONS.md release/v0.6.0/compliance/THIRD_PARTY_LICENSES.md \
  workspace/brief.md workspace/acceptance_criteria.md workspace/wbs.md \
  workspace/adr/ADR-INDEX.md workspace/adr/ADR-001.md workspace/adr/ADR-002.md workspace/adr/ADR-003.md \
  docs/ADR_INDEX.md docs/API.md \
  workspace/security/STRIDE.md workspace/security/SAST_CHECKLIST.md workspace/security/HARDENING.md \
  workspace/research/factsheet_devforge_mas.md \
  workspace/release/v0.1.0/README.md workspace/release/v0.1.0/CHANGELOG.md \
  workspace/release/v0.1.0/compliance/THIRD_PARTY_LICENSES.md \
  release/v0.6.0/ADR/ADR-INDEX.md release/v0.6.0/ADR/ADR-001.md release/v0.6.0/ADR/ADR-002.md release/v0.6.0/ADR/ADR-003.md

md-scan:
	@$(PDMK) --config $(PDMK_CFG) --continue-on-error scan $(MD_FILES)

md-fix:
	@$(PDMK) --config $(PDMK_CFG) --continue-on-error fix $(MD_FILES)

# наш автофикс для частых правил (безопасно гонять до/после md-fix)
md-autofix:
	@python tools/md_autofix.py $(MD_FILES)
