-- DevForge-MAS :: SQLite DDL (safe & backward-compatible, patched)
-- Цели рефакторинга:
-- 1) 💯 Сохранить существующие сущности и ограничения без регресса.
-- 2) 📈 Не уменьшать объём — добавлены индексы и служебные df_* таблицы.
-- 3) 🔄 Совместимость — df_* используются seed/smoke и не конфликтуют с «большой» схемой.
-- 4) 🧪 Предсказуемость — PRAGMA и комментарии для стабильных init/seed/smoke.

-- Безопасные дефолты для производительности и целостности:
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;

-- ==================================================================================
-- ОСНОВНАЯ МОДЕЛЬ (как была)
-- ==================================================================================

-- Projects
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  brief TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Brief versions
CREATE TABLE IF NOT EXISTS brief_versions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  version_tag TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(project_id, version_tag)
);

-- Acceptance Criteria
CREATE TABLE IF NOT EXISTS acceptance_criteria (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage TEXT NOT NULL CHECK (stage IN ('intake','research','planning','architecture','backend','frontend','release')),
  version_tag TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(project_id, stage, version_tag)
);

-- ADR-lite
CREATE TABLE IF NOT EXISTS adrs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  adr_code TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('proposed','accepted','deprecated','superseded','rejected')),
  context TEXT NOT NULL,
  decision TEXT NOT NULL,
  consequences TEXT NOT NULL,
  date_decided TEXT NOT NULL,
  supersedes TEXT,
  superseded_by TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(project_id, adr_code)
);

-- WBS: задачи и зависимости
CREATE TABLE IF NOT EXISTS wbs_tasks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  desc TEXT NOT NULL,
  stage TEXT CHECK (stage IN ('intake','research','planning','architecture','backend','frontend','release')),
  assignee TEXT,
  status TEXT NOT NULL,
  progress INTEGER NOT NULL CHECK (progress BETWEEN 0 AND 100),
  start_at TEXT,
  due_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(project_id, code)
);

CREATE TABLE IF NOT EXISTS wbs_task_deps (
  task_id TEXT NOT NULL REFERENCES wbs_tasks(id) ON DELETE CASCADE,
  depends_on TEXT NOT NULL REFERENCES wbs_tasks(id) ON DELETE CASCADE,
  PRIMARY KEY (task_id, depends_on),
  CHECK (task_id <> depends_on)
);

-- Artifacts
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage TEXT CHECK (stage IN ('intake','research','planning','architecture','backend','frontend','release')),
  path TEXT NOT NULL,
  type TEXT NOT NULL,
  produced_by TEXT,
  checksum TEXT,
  size_bytes INTEGER,
  mime TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(project_id, path)
);

-- Agents & runs
CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  version TEXT NOT NULL,
  capabilities TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
  stage TEXT NOT NULL,
  input_ref TEXT,
  output_ref TEXT,
  status TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  logs TEXT,
  created_at TEXT NOT NULL
);

-- Checks (основная таблица проекта; не путать с df_checks)
CREATE TABLE IF NOT EXISTS checks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  evidence_path TEXT,
  details TEXT,
  created_at TEXT NOT NULL
);

-- Events (аудит событий)
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- ==================================================================================
-- ИНДЕКСЫ ДЛЯ ОСНОВНОЙ МОДЕЛИ (безопасные IF NOT EXISTS)
-- ==================================================================================
CREATE INDEX IF NOT EXISTS idx_brief_versions_proj ON brief_versions(project_id);
CREATE INDEX IF NOT EXISTS idx_ac_proj_stage ON acceptance_criteria(project_id, stage);
CREATE INDEX IF NOT EXISTS idx_adrs_proj_code ON adrs(project_id, adr_code);
CREATE INDEX IF NOT EXISTS idx_wbs_tasks_proj ON wbs_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_wbs_tasks_stage ON wbs_tasks(stage);
CREATE INDEX IF NOT EXISTS idx_artifacts_proj ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_proj ON agent_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_checks_proj_stage ON checks(project_id, stage);
CREATE INDEX IF NOT EXISTS idx_events_proj ON events(project_id);

-- ==================================================================================
-- NAMESPACE ДЛЯ SMOKE/SEED (df_*) — НЕ КОНФЛИКТУЕТ С ОСНОВНОЙ МОДЕЛЬЮ
-- Эти таблицы используются db/queries/smoke_sqlite.sql и seed.sql
-- ==================================================================================

-- Простая WBS для smoke (не путать с wbs_tasks)
CREATE TABLE IF NOT EXISTS df_wbs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100)
);

-- Простые проверки для smoke (не путать с основной таблицей checks)
CREATE TABLE IF NOT EXISTS df_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  area TEXT NOT NULL,
  check_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('passed','failed','skipped')),
  artifact_path TEXT
);

-- Индексы для df_*-пространства
CREATE INDEX IF NOT EXISTS idx_df_wbs_status   ON df_wbs(status);
CREATE INDEX IF NOT EXISTS idx_df_checks_area  ON df_checks(area);
CREATE INDEX IF NOT EXISTS idx_df_checks_stat  ON df_checks(status);

-- ==================================================================================
-- (ОПЦИОНАЛЬНО) LEGACY-COMPAT VIEW'Ы — оставлено закомментированным
-- Если где-то остались скрипты, ожидающие "плоские" имена `wbs`/`checks` со
-- столбцами area/check_name, можно временно создать представления, не трогая
-- реальные таблицы. Для `checks` используйте имя checks_legacy (избегаем конфликта).
-- ==================================================================================
-- DROP VIEW IF EXISTS checks_legacy;
-- CREATE VIEW checks_legacy AS
--   SELECT area, check_name, status, artifact_path FROM df_checks;
--
-- DROP VIEW IF EXISTS wbs;  -- имя часто используется в легаси-скриптах
-- CREATE VIEW wbs AS
--   SELECT id, status, progress FROM df_wbs;

-- Конец файла
