#!/usr/bin/env bash
set -euo pipefail

CFG="config/ops.yaml"
JSON=$(python tools/ops/collect_metrics.py)
RED=$(printf '\033[31m'); GREEN=$(printf '\033[32m'); YELLOW=$(printf '\033[33m'); NC=$(printf '\033[0m')

errors=0

getjq() {
  python - <<'PY'
import sys, json
o=json.load(sys.stdin)
print(o)
PY
}

# Быстрый парсер через python (чтобы не требовать jq)
parse_field() {
  python - "$1" <<'PY'
import sys, json
data=json.loads(sys.stdin.read())
key=sys.argv[1]
# очень узко — не общий jq: используем в конкретных местах ниже
if key=="logs.errors":
    print(data["logs"]["errors"])
elif key=="logs.warns":
    print(data["logs"]["warns"])
elif key=="db.size_mb":
    print(data.get("db",{}).get("size_mb","0"))
else:
    print("")
PY
}

logs_errors=$(printf "%s" "$JSON" | parse_field "logs.errors")
logs_warns=$(printf "%s" "$JSON" | parse_field "logs.warns")
db_size_mb=$(printf "%s" "$JSON" | parse_field "db.size_mb")
db_limit=$(python -c 'import yaml;print(yaml.safe_load(open("config/ops.yaml"))["thresholds"]["db_max_size_mb"])')

if [ "${logs_errors:-0}" != "0" ]; then
  echo "${RED}[ALERT] Log errors: ${logs_errors}${NC}"
  errors=$((errors+1))
else
  echo "${GREEN}[OK] No log errors${NC}"
fi

if [ "${logs_warns:-0}" != "0" ]; then
  echo "${YELLOW}[WARN] Log warns: ${logs_warns}${NC}"
fi

# DB size
db_int=${db_size_mb%.*}
if [ -n "$db_int" ] && [ "$db_int" -gt "$db_limit" ]; then
  echo "${RED}[ALERT] SQLite DB size ${db_size_mb} MB > ${db_limit} MB${NC}"
  errors=$((errors+1))
else
  echo "${GREEN}[OK] SQLite DB size ${db_size_mb:-0} MB <= ${db_limit} MB${NC}"
fi

# Endpoints
backend_up=$(python - <<'PY' "$JSON"
import sys, json
o=json.loads(sys.argv[1])
b=o["endpoints"].get("backend_health")
print("UP" if b and b.get("up") else "DOWN")
PY
)
if [ "$backend_up" = "DOWN" ]; then
  echo "${RED}[ALERT] Backend health DOWN${NC}"
  errors=$((errors+1))
else
  echo "${GREEN}[OK] Backend health UP${NC}"
fi

# Артефакты свежие?
python - "$JSON" <<'PY'
import sys, json, yaml, time
Y="\033[33m"; G="\033[32m"; R="\033[31m"; N="\033[0m"
o=json.loads(sys.argv[1])
with open("config/ops.yaml","r",encoding="utf-8") as f:
    cfg=yaml.safe_load(f)
stale=float(cfg["thresholds"]["artifact_stale_hours"])
bad=0
for a in o["artifacts"]:
    p=a["path"]; ex=a["exists"]; age=a["age_h"]
    if not ex:
        print(f"{R}[ALERT] Missing artifact: {p}{N}")
        bad+=1
    else:
        if age is not None and age>stale:
            print(f"{R}[ALERT] Stale artifact (> {stale}h): {p} ({age:.1f}h){N}")
            bad+=1
        else:
            print(f"{G}[OK] {p}{N}")
if bad>0:
    sys.exit(2)
PY
artifacts_rc=$?

if [ $artifacts_rc -ne 0 ]; then
  errors=$((errors+1))
fi

if [ $errors -gt 0 ]; then
  echo "${RED}FAILED checks: $errors issue(s)${NC}"
  exit 2
fi

echo "${GREEN}All checks passed${NC}"
