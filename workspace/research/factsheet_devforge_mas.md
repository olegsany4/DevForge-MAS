# FactSheet — DevForge-MAS

## Assumptions

- Scope: фабрика приложений «от брифа до релизного артефакта» (код, README, тесты, CI, zip/DOCX/PDF), один этап = один чат.

- Целевая среда: macOS, Python 3.11+, Git, Make; опция локальных LLM (Ollama) и/или облачных.

- Архитектура: многоагентная оркестрация (Supervisor→Planner→Researcher→Architect→Dev→QA→Release) с контрактными артефактами.

- Репродьюсабельность: пин зависимостей, seed-детерминизм, фикс-промпты, ADR-lite, golden-тесты.

- Безопасность: песочница для запуска кода, политика доступа к I/O/сети.

- Качество: Acceptance Criteria на каждый шаг (валидаторы, линтеры, юнит-тесты).

- Хранилище контекста: Brief/AC/ADR/WBS/Artifacts как файлы в `workspace/`.

## References (публичные)

1. LangGraph (multi-agent state graphs)

2. Microsoft AutoGen (multi-agent patterns)

3. CrewAI (role-based agent teams)

4. LlamaIndex Agents/Tools

5. OpenDevin (auto-coding workflows)

6. Guardrails.ai (LLM-валидация по схемам)

7. Dify.ai Workflows/Agents

8. Semgrep (статический анализ/политики)

## Comparable Apps (≤3)

- OpenDevin — авто-разработка/редактирование кода.

- AutoGen (MSFT) — шаблоны кооперации агентов.

- Dify Workflows — визуальные пайплайны (менее код-центрично).

## Risks → Mitigations

- Галлюцинации LLM → фикс-промпты, low-temp, schema-валидаторы (pydantic/Guardrails), RAG.

- Нерепродьюсабельность → lock-файлы, seed, ADR-lite, snapshots/golden-тесты.

- Security/Tool abuse → песочница FS, явные разрешения, audit-лог, Semgrep, секреты в .env/vault.

- Долги по качеству → ruff/mypy, тест-порог, архитектурные проверки.

- Стоимость/латентность → локальные модели (Ollama), кэширование, лимиты токенов.

- Vendor lock-in → абстракция LLM-клиента, мульти-провайдер, fallback на локальные модели.

- Порча артефактов → dry-run, write-new-then-swap, snapshot/rollback.

- Срыв этапа → AC-гейты, чек-листы, останов/перезапуск при невыполнении.
