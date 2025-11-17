# monitoring.mk — цели локального мониторинга DevForge-MAS
# ВНИМАНИЕ: после целей ОБЯЗАТЕЛЬНО табы (не пробелы)

MON_PY := tools/monitor
MON_WS := workspace/.monitor

.PHONY: monitor-once monitor monitor-tui alerts alerts-daemon logs-tail health mark-green lint-report bandit-report

monitor-once:
	@python $(MON_PY)/collect.py --once && echo "[OK] metrics collected -> $(MON_WS)/state.json"

monitor:
	@python $(MON_PY)/collect.py --interval 5

monitor-tui: monitor-once
	@python $(MON_PY)/tui.py

alerts: monitor-once
	@python $(MON_PY)/alerts.py || true

alerts-daemon:
	@while true; do $(MAKE) alerts; sleep 30; done

logs-tail:
	@mkdir -p workspace/.logs && touch workspace/.logs/devforge-`date +%F`.jsonl
	@tail -f workspace/.logs/devforge-`date +%F`.jsonl

health: monitor-once alerts
	@echo "[Health] snapshot & alerts evaluated."

mark-green:
	@mkdir -p workspace/.checks
	@date -Iseconds > workspace/.checks/last_green.ts
	@echo "[OK] last green marked"

lint-report:
	@mkdir -p workspace/.checks
	@. .venv/bin/activate 2>/dev/null || true; ruff check . | tee /tmp/ruff.out || true
	@python - <<'PY'
import json, pathlib, re
txt = pathlib.Path("/tmp/ruff.out").read_text(encoding="utf-8", errors="ignore")
m = re.search(r'Found (\d+) error', txt)
issues = int(m.group(1)) if m else 0
(pathlib.Path("workspace/.checks")/"lint.json").write_text(json.dumps({"issues": issues}))
print(f"[lint-report] issues={issues}")
PY

bandit-report:
	@. .venv/bin/activate 2>/dev/null || true; bandit -r -f json -o bandit_report.json src tools || true
