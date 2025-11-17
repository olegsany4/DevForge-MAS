#!/usr/bin/env python3
# tools/db_smoke_sqlite.py
from __future__ import annotations

import json
import os
import sqlite3
import sys
from typing import Any, Iterable

# === Изменения (safe) ===
# 1) Сохранён публичный API и формат вывода: печатаем ТОЛЬКО {"wbs": ..., "checks": ...}.
# 2) Добавлена расширенная диагностика в stderr:
#    - PRAGMA: journal_mode, foreign_keys, synchronous
#    - Наличие базовых таблиц: projects, adrs, acceptance_criteria, df_wbs, df_checks
#    - Наличие индексов: idx_df_wbs_status, idx_df_checks_area
#    - Кол-во записей в df_wbs/df_checks (как sanity-check после seed)
# 3) Строгий режим по переменной окружения SMOKE_STRICT=1 — при проблемах exit(2).
# 4) Аннотации типов приведены к современному стилю (tuple[Any, ...] и т.д.).
# 5) Управление ресурсами через context manager.
# 6) [NEW] Безопасный подсчёт строк `_count()` без B608: имя таблицы whitelisted через PRAGMA.
#
# Замечание: Любые ошибки SQLite по-прежнему пробрасываются исключением.

DB = os.environ.get("DB_FILE", "devforge_mas.sqlite3")
SMOKE_STRICT = os.environ.get("SMOKE_STRICT", "0") == "1"
SMOKE_VERBOSE = os.environ.get("SMOKE_VERBOSE", "0") == "1"

# Алиасы типов для ясности и будущих расширений:
Row = tuple[Any, ...]
Rows = list[Row]
Params = Iterable[Any]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    # Включаем FK для каждого соединения (SQLite — per-connection setting)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error:
        pass
    return conn


def q(sql: str, params: Params = ()) -> Rows:
    """
    Утилита для быстрых smoke-запросов в локальную SQLite.

    Возвращает: список кортежей значений (Rows).
    """
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        result: Rows = list(cur.fetchall())
        return result


def _pragma(name: str) -> str:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(f"PRAGMA {name}")
        row = cur.fetchone()
        return "" if row is None else str(row[0])


def _table_exists(name: str) -> bool:
    sql = "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
    return len(q(sql, (name,))) > 0


def _index_exists(name: str) -> bool:
    sql = "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?"
    return len(q(sql, (name,))) > 0


# === [NEW] безопасные помощники для списков таблиц/валидации имени ===
def _list_tables() -> set[str]:
    """
    Возвращает множество имён таблиц в БД (нижний регистр).
    Используем PRAGMA table_list, где доступно (SQLite >= 3.37), с фолбэком на sqlite_master.
    """
    try:
        rows = q("PRAGMA table_list")
        if rows:
            # Формат: [schema, name, type, ncol, wr, strict] — имя обычно во 2-м столбце (index 1)
            return {str(r[1]).lower() for r in rows if len(r) > 1}
    except sqlite3.Error:
        # Переходим на фолбэк ниже
        pass
    # Фолбэк: sqlite_master
    rows2 = q("SELECT name FROM sqlite_master WHERE type='table'")
    return {str(r[0]).lower() for r in rows2 if r and r[0] is not None}


def _is_known_table(name: str) -> bool:
    """
    Проверяем, что таблица реально существует (case-insensitive).
    Это «whitelist»-проверка перед интерполяцией имени таблицы в SQL.
    """
    return str(name).lower() in _list_tables()


def _count(table: str) -> int:
    """
    Безопасный подсчёт количества строк в таблице.

    - Имя таблицы валидируется через PRAGMA/`sqlite_master` перед подстановкой.
    - Только после валидации используем f-string (иначе B608).
    - На несуществующую таблицу возвращаем 0 (как и раньше — мягкая деградация).
    """
    try:
        # СТАРАЯ версия (оставлена для обратимости и сравнения):
        # rows = q(f"SELECT COUNT(*) FROM {table}")
        # return int(rows[0][0]) if rows else 0

        # НОВАЯ безопасная версия:
        if not _is_known_table(table):
            return 0
        rows = q(f"SELECT COUNT(*) FROM {table}")  # nosec B608 — имя whitelisted в _is_known_table
        return int(rows[0][0]) if rows else 0
    except sqlite3.Error:
        return 0


def _diagnostics() -> dict[str, Any]:
    diag: dict[str, Any] = {}

    # PRAGMAs
    diag["pragma"] = {
        "journal_mode": _pragma("journal_mode"),
        "foreign_keys": _pragma("foreign_keys"),
        "synchronous": _pragma("synchronous"),
    }

    # Tables
    must_tables = [
        "projects",
        "adrs",
        "acceptance_criteria",
        "df_wbs",
        "df_checks",
    ]
    diag["tables"] = {t: _table_exists(t) for t in must_tables}

    # Indexes (df_* namespace)
    must_indexes = [
        "idx_df_wbs_status",
        "idx_df_checks_area",
    ]
    diag["indexes"] = {i: _index_exists(i) for i in must_indexes}

    # Counts for seed sanity
    diag["counts"] = {
        "df_wbs": _count("df_wbs"),
        "df_checks": _count("df_checks"),
    }

    return diag


def _print_diag(diag: dict[str, Any]) -> None:  # noqa: PLR0912
    # Лаконичная печать в stderr (не ломаем JSON stdout)
    print("[db_smoke_sqlite] diagnostics:", file=sys.stderr)
    print(json.dumps(diag, ensure_ascii=False, indent=2), file=sys.stderr)

    # Быстрые подсказки, если что-то не так:
    problems: list[str] = []

    # PRAGMA expectations
    if diag["pragma"].get("journal_mode", "").upper() != "WAL":
        problems.append("PRAGMA journal_mode != WAL")
    if diag["pragma"].get("foreign_keys", "0") not in ("1", "on", "ON", "true", "True"):
        problems.append("PRAGMA foreign_keys is not enabled")
    # synchronous допускаем NORMAL или FULL; если другое — предупреждение
    if str(diag["pragma"].get("synchronous", "")).upper() not in ("1", "2", "NORMAL", "FULL"):
        problems.append("PRAGMA synchronous is not NORMAL/FULL")

    # Tables
    for t, ok in diag.get("tables", {}).items():
        if not ok:
            problems.append(f"table missing: {t}")

    # Indexes
    for i, ok in diag.get("indexes", {}).items():
        if not ok:
            problems.append(f"index missing: {i}")

    # Counts
    if diag["counts"].get("df_wbs", 0) < 1:
        problems.append("df_wbs count < 1 (seed?)")
    if diag["counts"].get("df_checks", 0) < 1:
        problems.append("df_checks count < 1 (seed?)")

    if problems:
        print("[db_smoke_sqlite] WARN:", file=sys.stderr)
        for p in problems:
            print(f" - {p}", file=sys.stderr)
        if SMOKE_STRICT:
            # в строгом режиме падаем ненулевым кодом
            print("[db_smoke_sqlite] STRICT mode: failing due to problems above.", file=sys.stderr)
            sys.exit(2)
    elif SMOKE_VERBOSE:
        print("[db_smoke_sqlite] OK: all checks passed.", file=sys.stderr)


def main() -> None:
    # Запускаем расширенную диагностику (stderr), не ломая stdout-формат
    try:
        diag = _diagnostics()
        _print_diag(diag)
    except sqlite3.Error as e:
        print(f"[db_smoke_sqlite] sqlite diagnostics error: {e}", file=sys.stderr)
        # Продолжаем, чтобы основной вывод всё же попытаться отдать

    # Оригинальный однострочный вариант оставлен в комментарии для сравнения:
    # "SELECT "
    # "  stage, "
    # "  name, "
    # "  status, "
    # "  COALESCE(evidence_path, '') AS proof "
    # "FROM checks "
    # "ORDER BY datetime(created_at) DESC "
    # "LIMIT 10"

    checks_sql = """
        SELECT
          stage,
          name,
          status,
          COALESCE(evidence_path, '') AS proof
        FROM checks
        ORDER BY datetime(created_at) DESC
        LIMIT 10
    """.strip()

    try:
        data = {
            "wbs": q("SELECT code, status, progress FROM wbs_tasks ORDER BY code"),
            "checks": q(checks_sql),
        }
    except sqlite3.Error as e:
        print(f"[db_smoke_sqlite] sqlite error: {e}", file=sys.stderr)
        raise

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
