# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0-rc.1] - 2025-11-10

### Added

- Release-пайплайн Integrator: сборка `tar.gz`, `SHA256SUMS`, `RELEASE_NOTES`, `SBOM-lite`, reproducibility hash.
- Минимальный gate перед упаковкой: lint, tests, bandit, compliance-file-check, DB-smoke.
- Скрипт верификации релиза `tools/release_verify.py`.
- Makefile-цели: `release`, `dist`, `checksum`, `sbom-lite`, `verify-release`.

### Changed

- Унификация путей артефактов для переносимости (workspace/.checks, compliance/*, scripts/sqlite/*).
- Уточнение семантической версии (pre-release tag rc.1).

### Known Issues

- Предупреждения `Makefile: overriding commands` (несколько дублирующих целей). Не влияет на сборку релиза; запланировано к устранению в следующем релизе.
