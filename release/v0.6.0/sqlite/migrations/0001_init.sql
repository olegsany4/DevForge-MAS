-- 0001_init.sql — базовая инициализация SQLite для DevForge-MAS
-- Безопасный дефолт: включаем WAL, foreign_keys, строгие типы.

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;

-- Версионирование схемы (служебная таблица)
CREATE TABLE IF NOT EXISTS schema_migrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    version       INTEGER NOT NULL UNIQUE,
    applied_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Таблица WBS (план работ)
CREATE TABLE IF NOT EXISTS wbs (
    id        TEXT PRIMARY KEY,
    status    TEXT NOT NULL CHECK (status IN ('todo','in_progress','blocked','done')),
    progress  INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100)
);

-- Таблица checks (артефакты и статусы проверок)
CREATE TABLE IF NOT EXISTS checks (
    stage         TEXT NOT NULL,
    name          TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('passed','failed','skipped')),
    artifact_path TEXT NOT NULL,
    PRIMARY KEY (stage, name)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_wbs_status    ON wbs(status);
CREATE INDEX IF NOT EXISTS idx_checks_status ON checks(status);

-- Начальные данные (минимум для smoke)
INSERT OR IGNORE INTO wbs (id, status, progress) VALUES
  ('T01','in_progress',30),
  ('T02','todo',0),
  ('T03','todo',0);

INSERT OR IGNORE INTO checks (stage, name, status, artifact_path) VALUES
  ('research','verify-stage1','passed','workspace/.checks/research.md5');

-- Отметим применённую версию миграции
INSERT OR IGNORE INTO schema_migrations(version) VALUES (1);
