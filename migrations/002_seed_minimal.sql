-- Минимальные фикстуры под старт проекта DevForge-MAS

-- Project
INSERT INTO projects (key, name, brief)
VALUES
 ('DFMAS','DevForge-MAS','Мультиагентная фабрика приложений. Принцип: качество>скорость. Все решения в ADR-lite. Стейдж-гейты с проверками make verify-*.')
RETURNING id \gset

-- Brief v1
INSERT INTO brief_versions (project_id, version_tag, content)
VALUES (:id, to_char(now(), '"v"YYYY-MM-DD"T"HH24:MI:SS"Z"'),
        'Изначальный бриф. Требуется создать конвейер от Intake до Release с проверками.');

-- AC для первых стадий
INSERT INTO acceptance_criteria (project_id, stage, version_tag, payload)
VALUES
  (:id, 'intake',      'v1', '{"must":["Создан Project Brief","Определены KPI и ограничения"]}'),
  (:id, 'research',    'v1', '{"must":["Созданы AC/ADR/WBS черновики","Папки workspace/*"],"verify":["make verify-stage1"]}'),
  (:id, 'planning',    'v1', '{"must":["WBS покрывает все этапы","Дедлайны и зависимости"],"verify":["make verify-planning"]}'),
  (:id, 'architecture','v1', '{"must":["ADR count ≥ 10","Контракты API/Схемы"],"verify":["make verify-architect"]}');

-- Базовые ADR
INSERT INTO adrs (project_id, adr_code, title, status, context, decision, consequences, date_decided)
VALUES
  (:id,'ADR-0001','БД: PostgreSQL c опцией SQLite для локалки','accepted',
   'Нужна реплицируемая и предсказуемая СУБД',"PostgreSQL 15+ как основная, SQLite для single-node dev",
   'Единый DDL, упрощения в SQLite', now()),
  (:id,'ADR-0002','Стадии процесса фиксируются типом enum stage','accepted',
   'Нужна строгая трассируемость стадий', 'Вводим тип stage + проверки', 'Единообразная аналитика', now());

-- Базовые задачи WBS
INSERT INTO wbs_tasks (project_id, code, desc, stage, status, progress)
VALUES
  (:id,'T01','Уточнить Project Brief, KPI, ограничения','intake','in_progress',30),
  (:id,'T02','Завести ADR-lite реестр и шаблон','research','todo',0),
  (:id,'T03','Собрать WBS + статусы + зависимости','planning','todo',0);

-- Агенты
INSERT INTO agents (name, role, version, capabilities)
VALUES
 ('Supervisor','Управление стадиями и переносимость', '1.0.0', '{"snapshot":true,"gates":true}'),
 ('Architect','Архитектура/контракты','1.0.0','{"adr":true,"api":true}'),
 ('Backend','Бэкенд/интеграции','1.0.0','{"python":true}'),
 ('Frontend','UI','1.0.0','{"vite":true}'),
 ('QA','Проверки/тесты','1.0.0','{"pytest":true}');

-- Проверка-лог (пример)
INSERT INTO checks (project_id, stage, name, status, evidence_path, details)
VALUES
  (:id,'research','verify-stage1','passed','workspace/.checks/research.md5','{"files":7}');
