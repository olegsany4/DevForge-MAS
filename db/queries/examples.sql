-- 1) Сводка по проекту
SELECT p.key, p.name, length(p.brief) AS brief_len,
       (SELECT count(*) FROM adrs a WHERE a.project_id=p.id) AS adr_count,
       (SELECT count(*) FROM wbs_tasks t WHERE t.project_id=p.id) AS task_count
FROM projects p WHERE p.key='DFMAS';

-- 2) Невыполненные задачи с блокировками
SELECT t.code, t.desc, t.status, array_agg(d2.code ORDER BY d2.code) AS blocked_by
FROM wbs_tasks t
LEFT JOIN wbs_task_deps d ON d.task_id=t.id
LEFT JOIN wbs_tasks d2 ON d2.id=d.depends_on
WHERE t.project_id=(SELECT id FROM projects WHERE key='DFMAS') AND t.status<>'done'
GROUP BY t.id;

-- 3) Последние проверки по стадиям
SELECT stage, name, status, evidence_path, created_at
FROM checks
WHERE project_id=(SELECT id FROM projects WHERE key='DFMAS')
ORDER BY created_at DESC LIMIT 20;

-- 4) Последние события/аудит
SELECT kind, created_at, payload FROM events
WHERE project_id=(SELECT id FROM projects WHERE key='DFMAS')
ORDER BY created_at DESC LIMIT 50;
