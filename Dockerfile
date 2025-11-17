# Stage 1: сборка Vite/React фронтенда
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Копируем обязательные файлы для установки зависимостей
COPY workspace/frontend/package.json workspace/frontend/package-lock.json* ./

# Устанавливаем зависимости (если есть package-lock.json — npm ci, иначе npm install)
RUN if [ -f "package-lock.json" ]; then \
      npm ci; \
    else \
      npm install; \
    fi

# Копируем остальной код фронтенда и собираем
COPY workspace/frontend/ .

RUN npm run build

# Stage 2: backend + runtime
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    DB_FILE=/app/data/devforge_mas.sqlite3

WORKDIR /app

# Системные зависимости:
# - build-essential для сборки Python-зависимостей
# - sqlite3 для утилиты sqlite3 (make sqlite-init внутри контейнера)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Копируем метаданные Python-проекта
COPY pyproject.toml ./

# Копируем исходники и workspace
COPY src ./src
COPY workspace ./workspace

# Устанавливаем зависимости и сам пакет
# ВАЖНО: явно ставим fastapi, т.к. пакет devforge-mas не тянет его сам
RUN pip install --upgrade pip \
    && pip install "fastapi" "gunicorn" "uvicorn[standard]" \
    && pip install .

# Копируем собранный фронтенд в ожидаемую директорию внутри backend
# Ожидается, что backend уже умеет отдавать статику из workspace/frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./workspace/frontend/dist

# Директория и файл для SQLite (том будет примонтирован в /app/data)
RUN mkdir -p /app/data \
    && touch "${DB_FILE}"

EXPOSE 5000

# Запуск backend в production-режиме через gunicorn + uvicorn worker.
# При необходимости отредактируй путь к приложению:
#   workspace.backend.main:app
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:5000", "workspace.backend.main:app"]
