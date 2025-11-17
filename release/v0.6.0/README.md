# DevForge-MAS (MVP)

Мультиагентный пайплайн, который по текстовому заданию планирует работу, проектирует структуру и генерирует каркас приложения (код, README, тесты), складывая всё в `workspace/app/`.

## Быстрый старт

```bash
make install
make run

# DevForge-MAS — Multi-Agent App Factory

> Supervisor-подход: «качество > скорость», ADR-lite фиксация решений, воспроизводимость и проверяемость на каждом этапе.

## Требования

- macOS, Xcode CLT (`xcode-select --install`)
- Python 3.11.6 (`pyenv` рекомендован)
- `make`, `jq`, `sqlite3`
- Рекомендуется: `pyenv`, `direnv`

## Быстрый старт (Quickstart)

```bash

# 1) Python 3.11.6

pyenv shell 3.11.6

# 2) Установка окружения

python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# 3) Проверка базовых стадий/линта/тестов

make verify-stage1           # Research: OK/ПРОЙДЕН (смотри логи)
make verify-architect        # Архитектура: ADR/Contracts/Layouts
make lint                    # SAFE-линт (исключая src/)
make lint LINT_ALL=1         # Полный линт (включая src/)
pytest -q                    # Юнит-тесты

# 4) Инициализация SQLite (локальная разработка)

export DB_FILE="devforge_mas.sqlite3"
make sqlite-init
make sqlite-smoke
make sqlite-tables

# 5) Запуск back-/front-end (если включены в проект)

make backend-install
make backend-dev
make frontend-install
make frontend-dev

# или сборка и предпросмотр

make frontend-build
make frontend-preview

# DevForge-MAS — мультиагентная фабрика приложений

Супервизорная платформа для доведения задачи от брифа до релизного артефакта c фокусом на:


- **качество > скорость**

- фиксацию решений в **ADR-lite**

- **воспроизводимость** окружения и сборок

## Quickstart

```bash
pyenv shell 3.11.6
python3 -m venv .venv
. .venv/bin/activate

# Базовые зависимости проекта

pip install -r requirements.txt

# Dev-инструменты (линтеры, pytest, httpx и т.п.)

make dev-install

# DevForge-MAS

Мультиагентная фабрика приложений: от брифа до релизных артефактов с контролем качества, тестами и безопасностью.

## Quickstart (5 шагов)

```bash

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
make verify-all
