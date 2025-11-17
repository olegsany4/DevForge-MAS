# ADR-017: Packaging & Docker for DevForge-MAS

- Status: accepted
- Date: 2025-11-17
- Owner: Supervisor

## Context

DevForge-MAS включает:
- Python backend (workspace/backend, src/)
- Vite/React frontend (workspace/frontend)
- SQLite в качестве локальной БД (через переменную окружения `DB_FILE`)

Требования этапа:
- Production Dockerfile для backend (gunicorn + uvicorn worker)
- Сборка фронтенда (Vite → статик) и отдача UI из того же контейнера, что и API
- docker-compose.yml для локального запуска API+UI+SQLite одной командой

## Decision

1. Использовать один совместный Dockerfile в корне репозитория:
   - Многослойная сборка:
     - Stage 1: `node:20-alpine` для сборки Vite-фронтенда (`npm run build`).
     - Stage 2: `python:3.11-slim` для backend + runtime.
   - В рантайме:
     - Устанавливаем зависимости через `pip install .` по `pyproject.toml`.
     - Устанавливаем `gunicorn` и `uvicorn[standard]`.
     - Копируем собранный фронтенд в `workspace/frontend/dist`.
     - Запускаем `gunicorn` с воркером `uvicorn.workers.UvicornWorker` на `0.0.0.0:5000`.
     - Используем SQLite через `DB_FILE=/app/data/devforge_mas.sqlite3`.

2. Использовать `docker-compose.yml` в корне:
   - Один сервис `devforge-mas`:
     - `build: .` (Dockerfile по умолчанию).
     - Порты:
       - `5000:5000` — прямой доступ к API.
       - `80:5000` — доступ к UI через стандартный HTTP-порт.
     - Переменные окружения:
       - `PORT=5000`
       - `DB_FILE=/app/data/devforge_mas.sqlite3`
     - Том `devforge_mas_db:/app/data` для персистентного SQLite.

3. Инициализация SQLite при необходимости выполняется внутри контейнера
   (например, `make sqlite-init`), так как установлены `build-essential` и `sqlite3`.

## Consequences

- Плюсы:
  - Один контейнер обслуживает и API, и собранный UI.
  - `docker compose up --build` даёт полный стек (API+UI+SQLite).
  - Проект остаётся самодостаточным для локального запуска без внешней БД.
- Минусы:
  - Образ больше по размеру (Node+Python), чем при разделении на два контейнера.
  - Любое изменение Python-кода требует пересборки образа с `pip install .`.
- Возможные будущие улучшения:
  - Вынести фронтенд в отдельный контейнер (Nginx) для лучшего кеширования статики.
  - Вынести БД в PostgreSQL для production-сценариев.
