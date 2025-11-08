#!/usr/bin/env python3
import os, sqlite3, json

db = os.environ.get("DB_FILE", "devforge_mas.sqlite3")
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
con.execute("PRAGMA foreign_keys = ON;")

def q(sql):
    cur = con.execute(sql)
    return [dict(r) for r in cur.fetchall()]

report = {
    "projects": q("SELECT key,name,length(brief) AS brief_len FROM projects"),
    "adr":      q("SELECT adr_code,status FROM adrs ORDER BY adr_code"),
    "wbs":      q("SELECT code,status,progress FROM wbs_tasks ORDER BY code"),
    "checks":   q("SELECT stage,name,status,COALESCE(evidence_path,'') AS proof FROM checks ORDER BY datetime(created_at) DESC LIMIT 10"),
}
print(json.dumps(report, ensure_ascii=False, indent=2))
