# tests_db/test_sqlite_migrations.py
# Проверяет, что миграция 0001_init.sql успешно накатывается на чистую БД
# и создаёт ожидаемые таблицы/данные. Работает без внешних утилит sqlite3.

from __future__ import annotations

import sqlite3
from collections.abc import Iterator  # ruff UP035
from pathlib import Path

import pytest


def read_sql(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text


def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    try:
        yield conn
    finally:
        conn.close()


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def pragma(conn: sqlite3.Connection, key: str) -> str:
    cur = conn.execute(f"PRAGMA {key}")
    row = cur.fetchone()
    return "" if row is None else str(row[0])


@pytest.fixture()
def tmpdb(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite3"


def test_migration_0001_init_applies(tmpdb: Path):
    repo = Path(__file__).resolve().parents[1]
    mig = repo / "scripts" / "sqlite" / "migrations" / "0001_init.sql"
    assert mig.exists(), f"migration file missing: {mig}"

    sql = read_sql(mig)

    with connect(tmpdb) as conn:
        # applies script
        conn.executescript(sql)

        # PRAGMAs (диагностика, не все обязательны)
        jm = pragma(conn, "journal_mode").upper()
        fk = pragma(conn, "foreign_keys")
        assert jm in {"WAL", "MEMORY", "OFF"} or jm.isalpha()
        assert fk in {"1", "on", "ON", "true", "True"}

        # must-have tables (из миграции)
        for t in ("schema_migrations", "wbs", "checks"):
            assert table_exists(conn, t), f"table missing: {t}"

        # seed sanity
        cur = conn.execute("SELECT COUNT(*) FROM wbs")
        assert cur.fetchone()[0] >= 1
        cur = conn.execute("SELECT COUNT(*) FROM checks")
        assert cur.fetchone()[0] >= 1


def test_seed_scripts_are_consistent_with_ddl(tmpdb: Path):
    repo = Path(__file__).resolve().parents[1]
    ddl = repo / "scripts" / "sqlite" / "ddl.sql"
    seed = repo / "scripts" / "sqlite" / "seed.sql"
    assert ddl.exists(), f"DDL missing: {ddl}"
    assert seed.exists(), f"seed missing: {seed}"

    with connect(tmpdb) as conn:
        conn.executescript(ddl.read_text(encoding="utf-8"))
        conn.executescript(seed.read_text(encoding="utf-8"))

        # df_* namespace должен существовать и быть заполнен
        for t in ("df_wbs", "df_checks"):
            assert table_exists(conn, t), f"table missing: {t}"

        n_wbs = conn.execute("SELECT COUNT(*) FROM df_wbs").fetchone()[0]
        n_chk = conn.execute("SELECT COUNT(*) FROM df_checks").fetchone()[0]
        assert n_wbs >= 1, "df_wbs must have at least one row"
        assert n_chk >= 1, "df_checks must have at least one row"
