-- Демонстрационные артефакты и связи

-- Артефакты
INSERT INTO artifacts (project_id, stage, path, type, produced_by, checksum, mime)
SELECT id, 'research', 'workspace/PROJECT_BRIEF.md','doc','manual','sha256:DEMO1','text/markdown' FROM projects WHERE key='DFMAS';
INSERT INTO artifacts (project_id, stage, path, type, produced_by, checksum, mime)
SELECT id, 'architecture', 'workspace/CONTRACTS.json','doc','Architect','sha256:DEMO2','application/json' FROM projects WHERE key='DFMAS';

-- Прогон агента Architect на стадии architecture
WITH p AS (SELECT id AS project_id FROM projects WHERE key='DFMAS'),
     a AS (SELECT id AS agent_id FROM agents WHERE name='Architect' AND version='1.0.0')
INSERT INTO agent_runs (project_id, agent_id, stage, input_ref, output_ref, status, started_at, finished_at, logs)
SELECT p.project_id, a.agent_id, 'architecture',
       'workspace/ADR','workspace/CONTRACTS.json','succeeded',
       now() - interval '2 min', now(), 'OK: ADR=10, Contracts=5, Schemas=7'
FROM p,a;
