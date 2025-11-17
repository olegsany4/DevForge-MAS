-- DevForge-MAS :: SQLite seed (safe & backward-compatible)
-- Цели:
-- 1) 💯 Сохранить существующий функционал апсёртов в основные таблицы проекта.
-- 2) 📈 Не уменьшать объём файла: добавлены явные блоки и комментарии.
-- 3) 🔄 Совместимость: проблемные legacy-вставки в wbs/checks перенесены в df_*,
--    а исходные команды оставлены в LEGACY-блоке (закомментированы).
-- 4) 🧪 Работоспособность с первой попытки: не зависит от наличия legacy-таблиц.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ==================================================================================
-- 0) Подготовка: создаём "namespaced" таблицы, если их ещё нет (для smoke/sqlite)
-- ==================================================================================
CREATE TABLE IF NOT EXISTS df_wbs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS df_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  area TEXT NOT NULL,
  check_name TEXT NOT NULL,
  status TEXT NOT NULL,
  artifact_path TEXT
);

-- Индексы для df_checks
CREATE INDEX IF NOT EXISTS idx_df_checks_area ON df_checks(area);

-- ==================================================================================
-- 1) Projects
-- ==================================================================================
INSERT OR IGNORE INTO projects (id,key,name,brief,created_at,updated_at)
VALUES (
  'proj-1','DFMAS','DevForge-MAS',
  'Мультиагентная фабрика приложений. Принцип: качество>скорость. ADR-lite, стейдж-гейты make verify-*.',
  datetime('now'),datetime('now')
);

-- ==================================================================================
-- 2) Brief versions
-- ==================================================================================
INSERT OR IGNORE INTO brief_versions (id,project_id,version_tag,content,created_at)
VALUES ('brief-1','proj-1','v1','Первичная версия брифа',datetime('now'));

-- ==================================================================================
-- 3) Acceptance Criteria (основная модель)
-- ==================================================================================
INSERT OR IGNORE INTO acceptance_criteria (id,project_id,stage,version_tag,payload,created_at)
VALUES
 ('ac-1','proj-1','intake','v1','{"must":["Создан Project Brief","Определены KPI и ограничения"]}',datetime('now')),
 ('ac-2','proj-1','research','v1','{"must":["AC/ADR/WBS черновики","workspace/*"],"verify":["make verify-stage1"]}',datetime('now')),
 ('ac-3','proj-1','planning','v1','{"must":["WBS покрывает этапы","deps, сроки"],"verify":["make verify-planning"]}',datetime('now')),
 ('ac-4','proj-1','architecture','v1','{"must":["ADR >= 10","Контракты API/Схемы"],"verify":["make verify-architect"]}',datetime('now'));

-- ==================================================================================
-- 4) ADR-lite
-- ==================================================================================
INSERT OR IGNORE INTO adrs (id,project_id,adr_code,title,status,context,decision,consequences,date_decided,created_at,updated_at)
VALUES
 ('adr-1','proj-1','ADR-0001','БД: PostgreSQL + SQLite','accepted','Нужна предсказуемая БД','PostgreSQL в проде, SQLite локально','Единый DDL, упрощения SQLite',date('now'),datetime('now'),datetime('now')),
 ('adr-2','proj-1','ADR-0002','Тип stage фиксирует стадии','accepted','Нужна строгая трассировка стадий','Вводим stage-значения','Единая аналитика',date('now'),datetime('now'),datetime('now'));

-- ==================================================================================
-- 5) WBS (основная модель: wbs_tasks + deps)
-- ==================================================================================
INSERT OR IGNORE INTO wbs_tasks (id,project_id,code,desc,stage,status,progress,created_at,updated_at)
VALUES
 ('t-1','proj-1','T01','Уточнить Project Brief, KPI, ограничения','intake','in_progress',30,datetime('now'),datetime('now')),
 ('t-2','proj-1','T02','Завести ADR-lite реестр и шаблон','research','todo',0,datetime('now'),datetime('now')),
 ('t-3','proj-1','T03','Собрать WBS + статусы + зависимости','planning','todo',0,datetime('now'),datetime('now'));

-- Пример зависимостей (безопасно, если таблица существует)
-- INSERT OR IGNORE INTO wbs_task_deps (task_id, depends_on)
-- VALUES ('t-2','t-1'), ('t-3','t-1');

-- ==================================================================================
-- 6) Checks (основная модель проекта с полями project_id/stage/name/... )
-- ==================================================================================
INSERT OR IGNORE INTO checks (id,project_id,stage,name,status,evidence_path,details,created_at)
VALUES ('chk-1','proj-1','research','verify-stage1','passed','workspace/.checks/research.md5','{"files":7}',datetime('now'));

-- ==================================================================================
-- 7) Namespaced-данные для smoke (df_*): замена небезопасных legacy-вставок
-- ==================================================================================

-- Было (падало, если нет таблицы `wbs`):
--   DELETE FROM wbs;
--   INSERT INTO wbs (id, status, progress) VALUES
--     ('T01', 'in_progress', 30), ('T02', 'todo', 0), ('T03', 'todo', 0);
--
-- Делается теперь в df_wbs (стабильно и не конфликтует с основными схемами):
DELETE FROM df_wbs;
INSERT INTO df_wbs (id, status, progress) VALUES
  ('T01', 'in_progress', 30),
  ('T02', 'todo', 0),
  ('T03', 'todo', 0);

-- Было (падало, если таблица `checks` с другой схемой без колонок area/check_name):
--   DELETE FROM checks;
--   INSERT INTO checks (area, check_name, status, artifact_path) VALUES
--     ('research','verify-stage1','passed','workspace/.checks/research.md5');
--
-- Делается теперь в df_checks (стабильно и изолировано):
DELETE FROM df_checks;
INSERT INTO df_checks (area, check_name, status, artifact_path) VALUES
  ('research', 'verify-stage1', 'passed', 'workspace/.checks/research.md5');

COMMIT;

-- ==================================================================================
-- 8) LEGACY-СЕКЦИЯ (ЗАКОММЕНТИРОВАНА)
-- Если в старых скриптах/инструментах ещё используются таблицы `wbs` и "узкая" `checks`
-- (с колонками area/check_name/status/artifact_path), можно временно раскомментировать
-- секцию ниже. ⚠️ Делайте это только если схема таблиц соответствует указанным колонкам.
-- ==================================================================================

-- -- ⚠️ ВНИМАНИЕ: Вставки ниже вызовут ошибку, если `checks` имеет поля project_id/stage/name/...
-- -- Поэтому по умолчанию они отключены.
-- -- DELETE FROM wbs;
-- -- INSERT INTO wbs (id, status, progress) VALUES
-- --   ('T01', 'in_progress', 30),
-- --   ('T02', 'todo', 0),
-- --   ('T03', 'todo', 0);
-- --
-- -- DELETE FROM checks;
-- -- INSERT INTO checks (area, check_name, status, artifact_path) VALUES
-- --   ('research', 'verify-stage1', 'passed', 'workspace/.checks/research.md5');

-- Конец файла
