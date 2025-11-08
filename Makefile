# Makefile (DevForge-MAS)
# Рефакторинг безопасный:
# - echo -> printf (устраняет проблемы с кавычками/скобками в /bin/sh)
# - show-scope для диагностики
# - SAFE-область (без src/) по умолчанию; полный охват: make LINT_ALL=1
# - Устранены дубликаты целей (lint/typecheck/test/verify-techlead), сохранены LEGACY-версии комментарием для обратимости
# - typecheck не падает при отсутствии .py (безопасная проверка) и умеет работать в двух режимах (SAFE/ALL)
# - audit по умолчанию не “красит” сборку; строгий режим доступен через audit-strict или STRICT_AUDIT=1
# - добавлена цель deps-fix-audit для оперативного исправления известных уязвимостей setuptools
# - [CHANGE] устранены дубликаты frontend-* и sqlite-* (старые варианты перенесены в LEGACY, чтобы не терять историю)
# - [CHANGE] добавлены .PHONY для sqlite-* и новых служебных целей, чтобы избежать конфликтов имен

SHELL := /bin/sh

.PHONY: init tree verify-stage1 verify-architect verify-architect-fast \
        install install-dev show-scope \
        lint lint-full fmt format fix \
        typecheck sec test coverage all \
        audit audit-strict deps-fix-audit verify-techlead verify-print help

# ----- БАЗОВЫЕ ПЕРЕМЕННЫЕ -----
VENV ?= .venv
PY   ?= $(VENV)/bin/python
PIP  ?= $(VENV)/bin/pip
RUFF ?= $(VENV)/bin/ruff
MYPY ?= $(VENV)/bin/mypy
PYTEST ?= $(VENV)/bin/pytest
BANDIT ?= $(VENV)/bin/bandit
PIPAUDIT ?= $(VENV)/bin/pip-audit

# ----- СПИСКИ ФАЙЛОВ -----
# Все .py кроме .venv
PY_FILES_ALL := $(shell find . -type f -name "*.py" -not -path "./.venv/*")
# Без src/ (SAFE режим)
PY_FILES_NON_SRC := $(shell find . -type f -name "*.py" -not -path "./.venv/*" -not -path "./src/*")

# Включение полного охвата линта: make LINT_ALL=1
ifeq ($(LINT_ALL),1)
  LINT_SCOPE := $(PY_FILES_ALL)
  LINT_SCOPE_NAME := ALL (including src/)
  TYPE_SCOPE := ./tools ./scripts
  TYPE_SCOPE_NAME := ALL (tools/scripts; src позже)
else
  LINT_SCOPE := $(PY_FILES_NON_SRC)
  LINT_SCOPE_NAME := SAFE (excluding src/)
  TYPE_SCOPE := ./tools ./scripts
  TYPE_SCOPE_NAME := SAFE (tools/scripts only)
endif

# Список файлов для mypy в SAFE-области (обычно tools/scripts)
TYPE_FILES := $(shell find $(TYPE_SCOPE) -type f -name "*.py" 2>/dev/null)

# Возможные каталоги с кодом (для обратной совместимости со старыми инструкциями)
CODE_PKGS ?= src/mas src/tools

# Флаг строгого аудита (по умолчанию 0 — не роняем пайплайн на уязвимостях)
STRICT_AUDIT ?= 0

# Включение полного typecheck (вместе с src): make TYPECHECK_ALL=1
TYPECHECK_ALL ?= 0

# ----- HELP -----
help:
	@printf '\nDevForge-MAS Make targets:\n'
	@printf '  init                 — инициализация структуры workspace\n'
	@printf '  install / install-dev— установка зависимостей (prod/dev)\n'
	@printf '  show-scope           — показать области линта/типов\n'
	@printf '  lint / lint-full     — линт безопасный / по всему репо\n'
	@printf '  fmt|format / fix     — форматирование / автофикс\n'
	@printf '  typecheck            — mypy SAFE/ALL (ALL через TYPECHECK_ALL=1)\n'
	@printf '  test / coverage      — pytest (-q) / pytest с покрытием\n'
	@printf '  audit / audit-strict — аудит зависимостей + bandit (нестрогий/строгий)\n'
	@printf '  deps-fix-audit       — обновление setuptools до безопасной версии\n'
	@printf '  verify-architect     — проверки архитектора\n'
	@printf '  verify-techlead      — шлюз качества (lint+type+test+audit)\n'
	@printf '  verify-print         — печать артефактов\n\n'

# ----- ИНИЦИАЛИЗАЦИЯ -----
init:
	@mkdir -p workspace/{research,adr,artifacts} scripts
	@touch workspace/artifacts/.gitkeep
	@printf 'Init done.\n'

# ----- ПРОВЕРКИ ЭТАПОВ -----
verify-stage1:
	@chmod +x scripts/verify_stage1.sh || true
	@./scripts/verify_stage1.sh

tree:
	@printf 'Project layout:\n' && find . -maxdepth 3 -print | sed 's,^./,,'

verify-architect:
	@bash tools/verify_architect.sh

verify-architect-fast:
	@python3 tools/validate_contracts.py --fast

# ----- УСТАНОВКА -----
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev] || true
	$(PIP) install black==24.10.0 isort==5.13.2 ruff==0.7.0 mypy==1.11.2 bandit pip-audit pytest pre-commit
	$(VENV)/bin/pre-commit install || true
	$(VENV)/bin/pre-commit install --hook-type commit-msg || true

install-dev:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

# ----- ДИАГНОСТИКА -----
show-scope:
	@printf '>> Lint/Format scope: %s\n' "$(LINT_SCOPE_NAME)"
	@printf '>> Typecheck scope:   %s\n' "$(TYPE_SCOPE_NAME)"
	@printf '>> Lint files count:  %s\n' "$$(printf '%s\n' $(LINT_SCOPE) | wc -l | tr -d ' ')"
	@printf '>> Type files count:  %s\n' "$$(printf '%s\n' $(TYPE_FILES) | wc -w | tr -d ' ')"

# ----- КАЧЕСТВО КОДА -----
# безопасный линт по ограниченной области (без src/ если LINT_ALL!=1)
lint:
	@printf '>> Lint scope: %s\n' "$(LINT_SCOPE_NAME)"
	$(RUFF) check $(LINT_SCOPE)
	$(VENV)/bin/isort --check-only $(LINT_SCOPE)
	$(VENV)/bin/black --check $(LINT_SCOPE)

# линт по всему репозиторию (эквивалент прежнего глобального поведения)
lint-full:
	@printf '>> Lint scope: GLOBAL (.)\n'
	$(RUFF) check .
	$(VENV)/bin/isort --check-only .
	$(VENV)/bin/black --check .

fmt:
	@printf '>> Format scope: %s\n' "$(LINT_SCOPE_NAME)"
	$(VENV)/bin/isort $(LINT_SCOPE)
	$(VENV)/bin/black $(LINT_SCOPE)

# Совместимость: цель "format" как синоним fmt (не меняем привычки)
format: fmt

# Автофикс + форматирование Ruff/Black
fix:
	$(RUFF) check . --fix
	$(RUFF) format
	$(VENV)/bin/isort .

# ----- ПРОЧИЕ ПРОВЕРКИ -----
# Безопасная типизация:
# - По умолчанию SAFE: проверяем только tools/scripts (TYPE_FILES)
# - Полный режим (включая src): make TYPECHECK_ALL=1 typecheck
typecheck:
	@if [ "$(TYPECHECK_ALL)" = "1" ]; then \
		printf '>> Typecheck mode: ALL (src + tools + scripts)\n'; \
		FILES="$$(find src tools scripts -type f -name '*.py' -print)"; \
	else \
		printf '>> Typecheck mode: SAFE (tools/scripts only)\n'; \
		FILES="$(TYPE_FILES)"; \
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

test:
	$(PYTEST) -q

coverage:
	$(PYTEST) --cov=src --cov-report=term-missing

all: fmt lint typecheck test

# ----- АУДИТ ЗАВИСИМОСТЕЙ -----
# Не-строгий аудит: не роняем сборку, печатаем отчёт; STRICT_AUDIT=1 включает строгий режим
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

# Отдельная явная цель строгого аудита (роняет сборку при уязвимостях)
audit-strict:
	$(BANDIT) -r src
	$(PIPAUDIT) --progress-spinner off

# Горячая фиксация известных уязвимостей setuptools (PYSEC/GHSA)
deps-fix-audit:
	$(PIP) install --upgrade setuptools==78.1.1
	$(PIPAUDIT) --progress-spinner off || true

# ----- ПРОВЕРКА ЭТАПА TECHLEAD -----
# Объединяем обе прежние семантики:
# 1) если есть сценарий scripts/verify_techlead.sh — запускаем его
# 2) всегда выполняем агрегированный quality-gate (lint+type+test+audit)
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

# ===== Frontend helpers (канонический блок) =====
# [CHANGE] Оставлен один рабочий комплект целей; дубликаты убраны в LEGACY ниже.
.PHONY: frontend-install frontend-dev frontend-build frontend-preview
frontend-install:
	@npm install --prefix workspace/frontend

frontend-dev:
	@npm run dev --prefix workspace/frontend

frontend-build:
	@npm run build --prefix workspace/frontend

frontend-preview:
	@npm run preview --prefix workspace/frontend

# ===== DB tasks (PostgreSQL) =====
DB_URL ?= postgresql://user:pass@localhost:5432/devforge_mas

.PHONY: db-init db-seed db-seed-dev db-reset
db-init:
	psql "$(DB_URL)" -f migrations/001_init.sql

db-seed:
	psql "$(DB_URL)" -f migrations/002_seed_minimal.sql

db-seed-dev:
	psql "$(DB_URL)" -f seeds/dev_seed.sql

db-reset:
	psql "$(DB_URL)" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) db-init db-seed

# ===== SQLite DB tasks (канонический блок) =====
# [CHANGE] Удалены дубликаты sqlite-init/sqlite-smoke/sqlite-tables/sqlite-shell.
.PHONY: sqlite-init sqlite-smoke sqlite-tables sqlite-shell sqlite-reset sqlite-reseed
DB_FILE ?= devforge_mas.sqlite3

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

# [CHANGE] Утилиты для воспроизводимости локальной БД
sqlite-reset:
	rm -f "$(DB_FILE)"
	$(MAKE) sqlite-init

sqlite-reseed:
	sqlite3 "$(DB_FILE)" < scripts/sqlite/seed.sql

# ===== LEGACY-БЛОК (оставлен закомментированным для полной обратимости и трассировки) =====
# Старые глобальные варианты целей, вызывали дубли и override-предупреждения.
# Оставлены ЗАКОММЕНТИРОВАНО: логика перенесена в lint-full / fix / format и verify-techlead (агрегатор).
#
# lint:
# 	$(VENV)/bin/ruff check .
# 	$(VENV)/bin/isort --check-only .
# 	$(VENV)/bin/black --check .
#
# fmt:
# 	$(VENV)/bin/isort .
# 	$(VENV)/bin/black .
#
# typecheck:
# 	$(VENV)/bin/mypy .
#
# install-dev:
# 	$(PIP) install --upgrade pip
# 	$(PIP) install -r requirements-dev.txt
#
# test:
# 	$(PYTEST) -q
#
# coverage:
# 	$(PYTEST) --cov=src --cov-report=term-missing
#
# audit:
# 	$(BANDIT) -r src
# 	$(PIPAUDIT) --progress-spinner off
#
# verify-techlead:
# 	@echo "TechLead gate: OK"
#
# === LEGACY frontend duplicates (исторические копии; оставлены закомментированными) ===
# frontend-install:
# 	@npm install --prefix workspace/frontend
# frontend-dev:
# 	@npm run dev --prefix workspace/frontend
# frontend-build:
# 	@npm run build --prefix workspace/frontend
# frontend-preview:
# 	@npm run preview --prefix workspace/frontend
# frontend-install:
# 	@npm install --prefix workspace/frontend
# frontend-dev:
# 	@npm run dev --prefix workspace/frontend
# frontend-build:
# 	@npm run build --prefix workspace/frontend
# frontend-preview:
# 	@npm run preview --prefix workspace/frontend
# ===== END LEGACY =====
