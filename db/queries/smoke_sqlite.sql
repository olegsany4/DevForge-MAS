-- DevForge-MAS :: SQLite smoke query
-- Цели рефакторинга:
-- 1) 💯 Сохранить текущую семантику (снимки df_wbs/df_checks + вердикты).
-- 2) 📈 Не уменьшать объём: добавлены диагностические комментарии и LEGACY-секция.
-- 3) 🔄 Совместимость: оставлен закомментированный блок со снимками старых таблиц (wbs/checks).
-- 4) 🧪 Устойчивость: если DDL выполнен (scripts/sqlite/ddl.sql), скрипт стабильно отрабатывает.
--
-- ВАЖНО:
-- • SQLite не поддерживает условные SELECT по «не-существующей» таблице — планировщик
--   всё равно выдаст ошибку на этапе подготовки запроса. Поэтому, чтобы избежать ошибок,
--   сперва прогоните `make sqlite-init` (создаёт df_* таблицы), а затем — этот smoke.
-- • Если у вас всё ещё используются старые таблицы wbs/checks, раскомментируйте LEGACY-блок
--   внизу файла (он даёт аналогичные снимки по старым именам).

.headers on
.mode column

-- Небольшие диагностические строки
SELECT 'DevForge-MAS SQLite smoke' AS section;
SELECT 'Hint: run `make sqlite-init` before this script to ensure df_* tables exist.' AS note;

SELECT '';
SELECT 'Existing target tables' AS section;

SELECT name AS table_name
FROM sqlite_master
WHERE type='table' AND name IN ('df_wbs','df_checks')
ORDER BY name;

SELECT '';

-- =========================
-- WBS snapshot (df_wbs)
-- =========================
SELECT 'WBS snapshot (df_wbs)' AS section;
-- Таблица должна существовать (создаётся ddl.sql). Если нет — выполните make sqlite-init
SELECT * FROM df_wbs ORDER BY id;

SELECT '';

-- =========================
-- Checks snapshot (df_checks)
-- =========================
SELECT 'Checks snapshot (df_checks)' AS section;
-- Таблица должна существовать (создаётся ddl.sql). Если нет — выполните make sqlite-init
SELECT area, check_name, status, artifact_path
FROM df_checks
ORDER BY area, check_name;

SELECT '';

-- =========================
-- Вердикты по инициализации
-- =========================
SELECT 'Verdicts' AS section;

-- Вердикт по df_wbs
SELECT CASE
  WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='df_wbs')
   AND EXISTS (SELECT 1 FROM df_wbs) THEN 'OK: df_wbs entries exist'
  WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='df_wbs')
   AND NOT EXISTS (SELECT 1 FROM df_wbs) THEN 'FAIL: df_wbs exists but empty'
  ELSE 'SKIP: df_wbs not found (run make sqlite-init)'
END AS wbs_verdict;

-- Вердикт по df_checks
SELECT CASE
  WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='df_checks')
   AND EXISTS (SELECT 1 FROM df_checks WHERE status='passed') THEN 'OK: df_checks has at least one passed'
  WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='df_checks')
   AND NOT EXISTS (SELECT 1 FROM df_checks) THEN 'FAIL: df_checks exists but empty'
  WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='df_checks')
   AND NOT EXISTS (SELECT 1 FROM df_checks WHERE status='passed') THEN 'FAIL: df_checks has no passed'
  ELSE 'SKIP: df_checks not found (run make sqlite-init)'
END AS checks_verdict;

SELECT '';

-- =========================
-- Доп. диагностика (опционально)
-- Показываем структуру целевых таблиц, если они есть
-- =========================
SELECT 'Schemas (pragma table_info)' AS section;

-- ВАЖНО: не используем зарезервированное слово "table" как алиас; берём "tbl"
SELECT 'df_wbs' AS tbl, *
FROM pragma_table_info('df_wbs')
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='df_wbs');

SELECT 'df_checks' AS tbl, *
FROM pragma_table_info('df_checks')
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='df_checks');

SELECT '';

-- ============================================================================
-- LEGACY-COMPAT (ЗАКОММЕНТИРОВАНО):
-- Если вы ещё используете прежние имена таблиц wbs / checks, можете временно
-- раскомментировать блок ниже (или перенести эти запросы в отдельный файл
-- db/queries/smoke_sqlite_legacy.sql).
--
-- ВНИМАНИЕ: Если одновременно существуют и df_* и legacy-таблицы, снимки будут
-- дублироваться, поэтому не включайте этот блок без необходимости.
-- ============================================================================

-- -- LEGACY: список существующих legacy-таблиц
-- SELECT 'Legacy tables present' AS section;
-- SELECT name AS table_name
-- FROM sqlite_master
-- WHERE type='table' AND name IN ('wbs','checks')
-- ORDER BY name;
--
-- SELECT '';
--
-- -- LEGACY: WBS snapshot (wbs)
-- SELECT 'WBS snapshot (legacy: wbs)' AS section;
-- SELECT id, status, progress FROM wbs ORDER BY id;
--
-- SELECT '';
--
-- -- LEGACY: Checks snapshot (checks)
-- SELECT 'Checks snapshot (legacy: checks)' AS section;
-- SELECT area, check_name, status, artifact_path FROM checks ORDER BY area, check_name;
--
-- SELECT '';
--
-- -- LEGACY: Вердикты
-- SELECT 'Verdicts (legacy)' AS section;
-- SELECT CASE
--   WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='wbs')
--    AND EXISTS (SELECT 1 FROM wbs) THEN 'OK: wbs entries exist'
--   WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='wbs')
--    AND NOT EXISTS (SELECT 1 FROM wbs) THEN 'FAIL: wbs exists but empty'
--   ELSE 'SKIP: wbs not found'
-- END AS legacy_wbs_verdict;
--
-- SELECT CASE
--   WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='checks')
--    AND EXISTS (SELECT 1 FROM checks WHERE status='passed') THEN 'OK: checks has at least one passed'
--   WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='checks')
--    AND NOT EXISTS (SELECT 1 FROM checks) THEN 'FAIL: checks exists but empty'
--   WHEN EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='checks')
--    AND NOT EXISTS (SELECT 1 FROM checks WHERE status='passed') THEN 'FAIL: checks has no passed'
--   ELSE 'SKIP: checks not found'
-- END AS legacy_checks_verdict;

-- Конец файла
