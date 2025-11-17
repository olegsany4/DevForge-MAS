# MAKE targets

- `make help` — перечень целей
- `make install` / `dev-install` — окружение и зависимости
- `make fmt` — форматирование
- `make lint` — ruff + mypy (ALL/SAFE режим)
- `make test` — pytest
- `make test-coverage` — pytest + coverage html
- `make security-lint` — bandit (fail Medium/High)
- `make security-audit` — pip-audit
- `make sqlite-*` — инициализация и проверка SQLite
- `make frontend-*` — npm-скрипты (если `frontend/` существует)
- `make verify-all` — сводный «quality gate»
