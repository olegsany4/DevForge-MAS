PRAGMA foreign_keys = ON;

-- Проект
SELECT 'projects' AS t, key, name, length(brief) AS brief_len FROM projects;

-- ADR-lite
SELECT 'adrs' AS t, adr_code, status FROM adrs ORDER BY adr_code;

-- WBS
SELECT 'wbs_tasks' AS t, code, status, progress FROM wbs_tasks ORDER BY code;

-- Acceptance Criteria
SELECT 'ac' AS t, stage, version_tag, length(payload) AS bytes
FROM acceptance_criteria
ORDER BY stage, version_tag;

-- Последние проверки
SELECT 'checks' AS t, stage, name, status, COALESCE(evidence_path,'') AS proof
FROM checks
ORDER BY datetime(created_at) DESC
LIMIT 10;
