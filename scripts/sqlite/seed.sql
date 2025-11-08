PRAGMA foreign_keys = ON;

-- Projects
INSERT OR IGNORE INTO projects (id,key,name,brief,created_at,updated_at)
VALUES ('proj-1','DFMAS','DevForge-MAS','Мультиагентная фабрика приложений. Принцип: качество>скорость. ADR-lite, стейдж-гейты make verify-*.',datetime('now'),datetime('now'));

-- Brief versions
INSERT OR IGNORE INTO brief_versions (id,project_id,version_tag,content,created_at)
VALUES ('brief-1','proj-1','v1','Первичная версия брифа',datetime('now'));

-- Acceptance Criteria
INSERT OR IGNORE INTO acceptance_criteria (id,project_id,stage,version_tag,payload,created_at)
VALUES 
 ('ac-1','proj-1','intake','v1','{"must":["Создан Project Brief","Определены KPI и ограничения"]}',datetime('now')),
 ('ac-2','proj-1','research','v1','{"must":["AC/ADR/WBS черновики","workspace/*"],"verify":["make verify-stage1"]}',datetime('now')),
 ('ac-3','proj-1','planning','v1','{"must":["WBS покрывает этапы","deps, сроки"],"verify":["make verify-planning"]}',datetime('now')),
 ('ac-4','proj-1','architecture','v1','{"must":["ADR >= 10","Контракты API/Схемы"],"verify":["make verify-architect"]}',datetime('now'));

-- ADR-lite
INSERT OR IGNORE INTO adrs (id,project_id,adr_code,title,status,context,decision,consequences,date_decided,created_at,updated_at)
VALUES
 ('adr-1','proj-1','ADR-0001','БД: PostgreSQL + SQLite','accepted','Нужна предсказуемая БД','PostgreSQL в проде, SQLite локально','Единый DDL, упрощения SQLite',date('now'),datetime('now'),datetime('now')),
 ('adr-2','proj-1','ADR-0002','Тип stage фиксирует стадии','accepted','Нужна строгая трассировка стадий','Вводим stage-значения','Единая аналитика',date('now'),datetime('now'),datetime('now'));

-- WBS
INSERT OR IGNORE INTO wbs_tasks (id,project_id,code,desc,stage,status,progress,created_at,updated_at)
VALUES
 ('t-1','proj-1','T01','Уточнить Project Brief, KPI, ограничения','intake','in_progress',30,datetime('now'),datetime('now')),
 ('t-2','proj-1','T02','Завести ADR-lite реестр и шаблон','research','todo',0,datetime('now'),datetime('now')),
 ('t-3','proj-1','T03','Собрать WBS + статусы + зависимости','planning','todo',0,datetime('now'),datetime('now'));

-- Checks
INSERT OR IGNORE INTO checks (id,project_id,stage,name,status,evidence_path,details,created_at)
VALUES ('chk-1','proj-1','research','verify-stage1','passed','workspace/.checks/research.md5','{"files":7}',datetime('now'));
