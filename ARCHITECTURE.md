# Архитектура DevForge-MAS (кратко)

- **Цель**: мультиагентная сборка приложений по брифу → артефакты (код, docs, тесты).
- **Основные слои**:
  - `src/mas/core/*` — базовые абстракции (агенты, шина, воркфлоу)
  - `src/mas/agents/*` — конкретные роли (Supervisor/Reviewer/…)
  - `src/mas/tools/*` — утилиты (doc_builder, codegen, repo)
  - `src/mas/server/api.py` — легковесный API (если используется)
  - `tools/*` — вспомогательные скрипты (CI, smoke)
  - `scripts/sqlite/*` — DDL/seed для SQLite

**ADR-lite**: решения документируются в `workspace/adr/ADR-*.md` и сверяются на этапе Architect.

## Диаграмма (уровень контекста)
