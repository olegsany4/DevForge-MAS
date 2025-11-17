# tools/ops/logger.py
from __future__ import annotations

import json
import os
import pathlib
import socket
import sys
import time
import uuid
from dataclasses import asdict, dataclass

LOG_PATH = os.environ.get("OPS_LOG_FILE", "logs/devforge-mas.jsonl")
pathlib.Path(os.path.dirname(LOG_PATH)).mkdir(parents=True, exist_ok=True)


@dataclass
class LogEvent:
    ts: float
    run_id: str
    agent: str
    stage: str
    event: str
    status: str  # ok|warn|error
    message: str = ""
    meta: dict | None = None
    host: str = socket.gethostname()
    pid: int = os.getpid()
    ver: str = "1.0"


def emit(agent: str, stage: str, event: str, status: str = "ok", message: str = "", meta: dict | None = None, run_id: str | None = None):
    if run_id is None:
        run_id = os.environ.get("RUN_ID") or str(uuid.uuid4())
    rec = LogEvent(ts=time.time(), run_id=run_id, agent=agent, stage=stage, event=event, status=status, message=message, meta=meta)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
    # stderr echo for immediate visibility on warn/error
    if status in ("warn", "error"):
        print(f"[{status.upper()}] {stage}:{event} — {message}", file=sys.stderr)
