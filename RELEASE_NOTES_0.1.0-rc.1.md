# DevForge-MAS 0.1.0-rc.1 — Release Notes (Integrator)

**Фокус релиза:** воспроизводимая упаковка проекта с минимальным набором проверок качества и комплаенса.

## Состав bundle

- Архив: `devforge-mas-0.1.0-rc.1.tar.gz`

- Контрольные суммы: `SHA256SUMS`

- Отчет о зависимостях (SBOM-lite): `SBOM-LITE.txt`

- Сводка проверок: `release_report.txt`

- Версия: `VERSION`

- Changelog: `CHANGELOG.md`

- Release Notes: этот файл

## Краткий итог проверок

- Lint/tests — OK

- Bandit — OK (предупреждения не критичны)

- Compliance — OK (NOTICE/OBLIGATIONS/THIRD_PARTY_LICENSES на месте)

- DB smoke — OK (`tools/db_smoke_sqlite.py` / `db/queries/smoke_sqlite.sql`)

## Известные ограничения

- Дубли целей в Makefile → warning. Исправим в 0.1.0-rc.2.
