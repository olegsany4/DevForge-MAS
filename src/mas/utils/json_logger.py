# Назначение: единый JSON-логгер (stdout + rotation в workspace/.logs/)
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

LOG_DIR = pathlib.Path("workspace/.logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / f"devforge-{dt.date.today().isoformat()}.jsonl"

_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40, "CRITICAL": 50}
LEVEL = _LEVELS.get(os.getenv("LOG_LEVEL", "INFO").upper(), 20)


def _now_iso():
    return dt.datetime.now(dt.UTC).astimezone().isoformat()


def log(level: str, component: str, event: str, msg: str, **fields):
    if _LEVELS[level] < LEVEL:
        return
    rec = {
        "ts": _now_iso(),
        "level": level,
        "component": component,
        "event": event,
        "msg": msg,
        **fields,
    }
    line = json.dumps(rec, ensure_ascii=False)
    print(line, file=sys.stdout)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def info(component, event, msg, **kw):
    log("INFO", component, event, msg, **kw)


def warn(component, event, msg, **kw):
    log("WARN", component, event, msg, **kw)


def error(component, event, msg, **kw):
    log("ERROR", component, event, msg, **kw)


def debug(component, event, msg, **kw):
    log("DEBUG", component, event, msg, **kw)
