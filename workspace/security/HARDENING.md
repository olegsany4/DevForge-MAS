# DevForge-MAS — Меры Hardening

> Версия: 1.0 • Дата: 2025-11-08

## 1. Identity & Access

- Использовать сервис-аккаунты с PoLP для агентов, CI и БД.
- Короткоживущие токены; ротация секретов по расписанию.
- Подпись вебхуков HMAC; для внутреннего трафика — mTLS.

## 2. Secrets Management

- Секреты хранятся в Secret Manager/Vault/1Password; не в git.
- Переменные CI — защищённые/скоупленные по окружениям.
- OIDC в CI → временные облачные креды (“secret zero” не хранится).

## 3. Supply-Chain

- Pin+hash зависимостей; запрет `latest`.
- Internal mirror/proxy PyPI; контроль источников.
- SBOM (`syft`) и подпись артефактов (`cosign`/`sigstore`).

## 4. Runtime & Network

- Контейнерная изоляция, read-only root FS, non-root user.
- Сетевые egress-политики: только необходимый список доменов/APIs.
- Rate-limiters/квоты на LLM/API; circuit-breakers; backpressure.

## 5. Data & Logs

- Шифрование at-rest (БД/бэкапы) и in-transit (TLS 1.2+).
- Неизменяемое хранилище аудита (WORM/S3 Object Lock).
- Политики хранения/удаления чувствительных логов.

## 6. App Security

- Валидация входов (JSON Schema), лимиты на размер/тип.
- Запрет `eval/exec`; песочница для пользовательских шаблонов.
- Feature flags для отключения рискованных путей.

## 7. LLM Safety

- System-prompt неизменяем; контекст фильтруется.
- Санитайзеры HTML/URLs; защита от prompt-инъекций.
- Контроль бюджета: max-tokens/cost per job/org.

## 8. Resilience & Monitoring

- Таймауты/ретраи с jitter; DLQ; health-пробы.
- WAF/IDS на внешних входах.
- Оповещения: утечка ключа/исчерпание бюджета/DoS.

## 9. Процесс

- Security-гейт в CI обязателен для merge.
- Регулярные dependency-updates; ежемесячный отчёт уязвимостей.
- Тренировка инцидентов (table-top) раз в квартал.

### Сопутствующие файлы

- Чек-лист SAST → `workspace/security/SAST_CHECKLIST.md`
- STRIDE → `workspace/security/STRIDE.md`
- CI security workflow → `workspace/.ci/security.yml`
