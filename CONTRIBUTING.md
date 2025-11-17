# Contributing

Спасибо за вклад в DevForge-MAS! Этот документ описывает правила коммитов, ветвления, качество кода, тестирование и процесс релиза.

> Если что-то непонятно — открывайте issue или создавайте draft PR. Мы ценим инициативу.

---

## Коммит-правила

- Используем **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `build:`, `ci:`, `perf:`, `revert:`.
- Заголовок ≤ 72 символов, в теле — что и почему изменено, ссылки на issue/ADR при наличии.
- Один логический кусок работы — один коммит. Не смешивайте рефакторинг и функциональные изменения.

Примеры:

```text
feat(api): add /contracts?mode=parsed to return parsed JSON
fix(security): validate http/https scheme in collect_metrics (B310)
docs(contributing): clarify pre-commit and md rules (MD031)
