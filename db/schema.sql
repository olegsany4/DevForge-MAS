-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1) Справочники/типы
CREATE TYPE stage AS ENUM (
  'intake','research','planning','architecture','backend','frontend','release'
);

CREATE TYPE run_status AS ENUM ('queued','running','succeeded','failed','skipped','canceled');
CREATE TYPE check_status AS ENUM ('passed','failed','waived');
CREATE TYPE adr_status AS ENUM ('proposed','accepted','deprecated','superseded','rejected');
CREATE TYPE artifact_type AS ENUM ('doc','code','test','binary','image','archive','report','other');

-- 2) Проект и бриф
CREATE TABLE projects (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  key          TEXT UNIQUE NOT NULL,           -- короткий ключ (e.g., "DFMAS")
  name         TEXT NOT NULL,
  brief        TEXT NOT NULL,                  -- актуальная версия брифа (денормализация для скорости)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE brief_versions (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  version_tag  TEXT NOT NULL,                  -- e.g., "v2025-11-08T12:00Z"
  content      TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(project_id, version_tag)
);

-- 3) Acceptance Criteria (версионируемые)
CREATE TABLE acceptance_criteria (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage        stage NOT NULL,
  version_tag  TEXT NOT NULL,
  payload      JSONB NOT NULL,                 -- произвольная структура AC с таймштампами пунктов
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(project_id, stage, version_tag)
);

-- 4) ADR-lite
CREATE TABLE adrs (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id     UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  adr_code       TEXT NOT NULL,                -- "ADR-0001"
  title          TEXT NOT NULL,
  status         adr_status NOT NULL DEFAULT 'proposed',
  context        TEXT NOT NULL,
  decision       TEXT NOT NULL,
  consequences   TEXT NOT NULL,
  date_decided   DATE NOT NULL,
  supersedes     TEXT,                          -- "ADR-000X" (человеческая ссылка)
  superseded_by  TEXT,                          -- "ADR-000Y"
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(project_id, adr_code)
);

-- 5) WBS (задачи и зависимости)
CREATE TABLE wbs_tasks (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  code         TEXT NOT NULL,                  -- "T01"
  desc         TEXT NOT NULL,
  stage        stage,                          -- опционально привязать к стадии
  assignee     TEXT,                           -- кто отвечает
  status       TEXT NOT NULL DEFAULT 'todo',   -- todo/in_progress/done/blocked
  progress     INT NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  start_at     TIMESTAMPTZ,
  due_at       TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(project_id, code)
);

CREATE TABLE wbs_task_deps (
  task_id    UUID NOT NULL REFERENCES wbs_tasks(id) ON DELETE CASCADE,
  depends_on UUID NOT NULL REFERENCES wbs_tasks(id) ON DELETE CASCADE,
  PRIMARY KEY (task_id, depends_on),
  CHECK (task_id <> depends_on)
);

-- 6) Артефакты
CREATE TABLE artifacts (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage         stage,
  path          TEXT NOT NULL,                   -- относительный путь в workspace или URI
  type          artifact_type NOT NULL DEFAULT 'other',
  produced_by   TEXT,                            -- агент/скрипт/ручной
  checksum      TEXT,                            -- sha256
  size_bytes    BIGINT,
  mime          TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(project_id, path)
);

-- 7) Агенты и их запуски
CREATE TABLE agents (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT NOT NULL,                   -- "Architect", "Backend", "QA", ...
  role          TEXT NOT NULL,                   -- свободный текст роли
  version       TEXT NOT NULL DEFAULT '1.0.0',
  capabilities  JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(name, version)
);

CREATE TABLE agent_runs (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  agent_id      UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
  stage         stage NOT NULL,
  input_ref     TEXT,                            -- ссылка на входной артефакт/папку
  output_ref    TEXT,                            -- ссылка на результ. артефакт/папку
  status        run_status NOT NULL DEFAULT 'queued',
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ,
  logs          TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8) Проверки/вёрфикация этапов
CREATE TABLE checks (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage         stage NOT NULL,
  name          TEXT NOT NULL,                   -- "verify-architect", "lint", etc.
  status        check_status NOT NULL,
  evidence_path TEXT,                            -- артефакт-док-лог
  details       JSONB DEFAULT '{}'::jsonb,       -- метрики, числа, хэши, версии
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9) События/аудит
CREATE TABLE events (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL,                   -- "ADR_CHANGED", "CHECK_PASSED", ...
  payload       JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Индексы
CREATE INDEX idx_acceptance_criteria_proj_stage ON acceptance_criteria(project_id, stage);
CREATE INDEX idx_adrs_proj_status ON adrs(project_id, status);
CREATE INDEX idx_wbs_proj_status ON wbs_tasks(project_id, status);
CREATE INDEX idx_artifacts_proj_stage ON artifacts(project_id, stage);
CREATE INDEX idx_agent_runs_proj_stage ON agent_runs(project_id, stage);
CREATE INDEX idx_checks_proj_stage ON checks(project_id, stage);
CREATE INDEX idx_events_project ON events(project_id);
