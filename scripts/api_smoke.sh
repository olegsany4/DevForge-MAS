#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BASE="http://${HOST}:${PORT}"
VENV="${VENV:-.venv}"

need_kill=0
pid=""

log() { printf '%s\n' "$*" >&2; }

is_up() {
  curl -fsS "${BASE}/health" >/dev/null 2>&1
}

start_api() {
  log "API не отвечает — поднимаю временный uvicorn на ${BASE}"
  # Активируем venv и запускаем uvicorn без autoreload, чтобы корректно гасить по PID
  # shellcheck disable=SC1090
  source "${VENV}/bin/activate"
  uvicorn src.mas.server:app --host "${HOST}" --port "${PORT}" --no-access-log --log-level warning --no-server-header &
  pid=$!
  need_kill=1

  # Ждём готовности до 10 секунд
  for i in {1..20}; do
    if is_up; then
      log "API поднят (pid=${pid})"
      return 0
    fi
    sleep 0.5
  done

  log "Не удалось дождаться запуска API за 10с"
  exit 1
}

cleanup() {
  if [[ "${need_kill}" -eq 1 && -n "${pid}" ]]; then
    log "Гашу временный uvicorn (pid=${pid})"
    kill "${pid}" 2>/dev/null || true
    wait "${pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# 1) Проверяем доступность; если недоступен — поднимаем временно
if ! is_up; then
  start_api
fi

# 2) Пробы
echo ">>> /health"
curl -fsS "${BASE}/health" | jq .

echo ">>> /contracts"
curl -fsS "${BASE}/contracts" | jq .

log "Smoke OK"
