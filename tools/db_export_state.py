#!/usr/bin/env python3
# tools/db_export_state.py
from __future__ import annotations

import datetime
import json
import os
import sqlite3
from collections.abc import Iterable
from typing import Any

# Путь к базе берём из окружения, по умолчанию — локальный файл
DB = os.environ.get("DB_FILE", "devforge_mas.sqlite3")


def _rows(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> list[tuple[Any, ...]]:
    """
    Базовый извлекатель: выполняет запрос и возвращает list[tuple].
    Поведение идентично прежней версии (сохраняем совместимость).
    """
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    return cur.fetchall()


def _extract_first_table_name(query: str) -> str | None:
    """
    Наивно извлекаем имя таблицы после первого 'FROM' (без подзапросов/alias-ов).
    Нужно только для защитного режима _safe_rows, чтобы не падать,
    когда схемы ещё нет. Если имя распарсить не удалось — возвращаем None
    и позволяем выполниться как обычно (это будет видно тестами).
    """
    q = query.lower()
    if " from " not in q:
        return None
    # Берём фрагмент после первого ' from '
    tail = q.split(" from ", 1)[1].strip()
    # Отсекаем всё после пробела/перевода строки/табуляции/знаков
    stop_tokens = [" ", "\n", "\t", ";", "where", "order", "limit", "group", "left", "join"]
    cut = len(tail)
    for tok in stop_tokens:
        pos = tail.find(tok)
        if pos != -1:
            cut = min(cut, pos)
    candidate = tail[:cut].strip()
    # Удалим возможные кавычки/скобки
    return candidate.strip("`[]\"'()") or None


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,))
    return cur.fetchone() is not None


def _safe_rows(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> list[tuple[Any, ...]]:
    """
    Безопасный извлекатель:
    - Если целевая таблица отсутствует (например, не выполнен ddl.sql) — вернём пустой список,
      чтобы не валить пайплайн на ранних стадиях.
    - Иначе поведение такое же, как у _rows.
    """
    table = _extract_first_table_name(query)
    if table and not _table_exists(conn, table):
        return []
    return _rows(conn, query, params)


def export_state(project_id: str | None = None) -> dict[str, Any]:
    """
    Экспортирует сводное состояние артефактов проекта из SQLite.

    Возвращаемая структура:
    {
      "brief_versions": [...],
      "acceptance_criteria": [...],
      "adrs": [...],
      "wbs": [...],
      "checks": [...],
      "exported_at": "UTC ISO8601"
    }

    Совместимость:
    - Сигнатура и ключи результата прежние.
    - Добавлена «мягкая» устойчивость к отсутствующим таблицам (_safe_rows).
    """
    conn = sqlite3.connect(DB)
    try:
        pid = project_id

        # Короткие именованные SQL — читаемо и не нарушает E501 благодаря Black
        q_brief = "SELECT version_tag, created_at FROM brief_versions WHERE project_id = ? ORDER BY created_at DESC"
        q_ac = "SELECT stage, version_tag FROM acceptance_criteria WHERE project_id = ? ORDER BY stage, version_tag"
        q_adr = "SELECT adr_code, title, status, date_decided FROM adrs WHERE project_id = ? ORDER BY adr_code"
        q_wbs = "SELECT code, desc, stage, status, progress FROM wbs_tasks WHERE project_id = ? ORDER BY code"
        q_checks = "SELECT stage, name, status, evidence_path, created_at FROM checks WHERE project_id = ? ORDER BY datetime(created_at) DESC LIMIT 50"

        # Используем безопасный извлекатель, чтобы не падать на неполной схеме
        data: dict[str, Any] = {
            "brief_versions": _safe_rows(conn, q_brief, (pid,)) if pid else [],
            "acceptance_criteria": _safe_rows(conn, q_ac, (pid,)) if pid else [],
            "adrs": _safe_rows(conn, q_adr, (pid,)) if pid else [],
            "wbs": _safe_rows(conn, q_wbs, (pid,)) if pid else [],
            "checks": _safe_rows(conn, q_checks, (pid,)) if pid else [],
            "exported_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        return data
    finally:
        conn.close()


def main() -> None:
    project_id = os.environ.get("PROJECT_ID")
    state = export_state(project_id)
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
