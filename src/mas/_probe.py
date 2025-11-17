# src/mas/_probe.py
from __future__ import annotations


def health_probe() -> str:
    """Tiny callable used by tests to ensure we execute some code inside src/."""
    # простая логика, чтобы была хоть какая-то исполняемость
    return "OK"
