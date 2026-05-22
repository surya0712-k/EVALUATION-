from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Any, Optional, Tuple, Union

try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover - optional until Postgres is used
    psycopg2 = None  # type: ignore[assignment]

_backend_root = Path(__file__).resolve().parents[2]
_default_sqlite = str(_backend_root / "careerlens.db")
_RAW = os.getenv("DATABASE_URL", _default_sqlite).strip()


def _is_postgres_url(url: str) -> bool:
    u = url.lower()
    return u.startswith("postgresql://") or u.startswith("postgres://")


USE_POSTGRES = _is_postgres_url(_RAW)
# SQLite: file path string. Postgres: full DSN.
DB_PATH = _RAW

if USE_POSTGRES and psycopg2 is None:
    raise RuntimeError(
        "DATABASE_URL looks like PostgreSQL but psycopg2 is not installed. "
        "Run: pip install psycopg2-binary"
    )


class _PgConnection:
    """Minimal sqlite-like API on top of psycopg2 (positional `?` → `%s`)."""

    def __init__(self, raw: Any) -> None:
        self._raw = raw

    def execute(self, sql: str, params: Tuple[Any, ...] | list[Any] | None = None) -> Any:
        sql_pg = sql.replace("?", "%s")
        cur = self._raw.cursor()
        cur.execute(sql_pg, tuple(params) if params is not None else ())
        return cur

    def commit(self) -> None:
        self._raw.commit()

    def __enter__(self) -> "_PgConnection":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_type:
            self._raw.rollback()
        else:
            self._raw.commit()
        self._raw.close()


def get_conn() -> Union[sqlite3.Connection, _PgConnection]:
    if USE_POSTGRES:
        raw = psycopg2.connect(DB_PATH, cursor_factory=psycopg2.extras.RealDictCursor)
        return _PgConnection(raw)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_users_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(users)").fetchall()
    return {str(r[1]) for r in rows}


def _ensure_sqlite_user_profile_columns(conn: sqlite3.Connection) -> None:
    names = _sqlite_users_columns(conn)
    for col, ddl in (
        ("bio", "ALTER TABLE users ADD COLUMN bio TEXT"),
        ("job_title", "ALTER TABLE users ADD COLUMN job_title TEXT"),
        ("phone", "ALTER TABLE users ADD COLUMN phone TEXT"),
        ("avatar_url", "ALTER TABLE users ADD COLUMN avatar_url TEXT"),
        ("profile_complete", "ALTER TABLE users ADD COLUMN profile_complete INTEGER NOT NULL DEFAULT 1"),
    ):
        if col not in names:
            conn.execute(ddl)


def _sqlite_evaluation_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(evaluations)").fetchall()
    return {str(r[1]) for r in rows}


def _pg_users_columns(conn: _PgConnection) -> set[str]:
    cur = conn.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        ("users",),
    )
    rows = cur.fetchall()
    return {str(r["column_name"]) for r in rows}


def _ensure_pg_user_profile_columns(conn: _PgConnection) -> None:
    names = _pg_users_columns(conn)
    for col, ddl in (
        ("bio", "ALTER TABLE users ADD COLUMN bio TEXT"),
        ("job_title", "ALTER TABLE users ADD COLUMN job_title TEXT"),
        ("phone", "ALTER TABLE users ADD COLUMN phone TEXT"),
        ("avatar_url", "ALTER TABLE users ADD COLUMN avatar_url TEXT"),
        ("profile_complete", "ALTER TABLE users ADD COLUMN profile_complete INTEGER NOT NULL DEFAULT 1"),
    ):
        if col not in names:
            conn.execute(ddl)


def _pg_evaluation_columns(conn: _PgConnection) -> set[str]:
    cur = conn.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        ("evaluations",),
    )
    rows = cur.fetchall()
    return {str(r["column_name"]) for r in rows}


def _ensure_sqlite_snapshot_columns(conn: sqlite3.Connection) -> None:
    names = _sqlite_evaluation_columns(conn)
    for name, ddl in (
        ("github_data_json", "ALTER TABLE evaluations ADD COLUMN github_data_json TEXT"),
        ("linkedin_data_json", "ALTER TABLE evaluations ADD COLUMN linkedin_data_json TEXT"),
        ("pipeline_json", "ALTER TABLE evaluations ADD COLUMN pipeline_json TEXT"),
        ("user_id", "ALTER TABLE evaluations ADD COLUMN user_id INTEGER"),
    ):
        if name not in names:
            conn.execute(ddl)


def _ensure_pg_snapshot_columns(conn: _PgConnection) -> None:
    names = _pg_evaluation_columns(conn)
    for name, ddl in (
        ("github_data_json", "ALTER TABLE evaluations ADD COLUMN github_data_json TEXT"),
        ("linkedin_data_json", "ALTER TABLE evaluations ADD COLUMN linkedin_data_json TEXT"),
        ("pipeline_json", "ALTER TABLE evaluations ADD COLUMN pipeline_json TEXT"),
        ("user_id", "ALTER TABLE evaluations ADD COLUMN user_id INTEGER"),
    ):
        if name not in names:
            conn.execute(ddl)


def _init_sqlite(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            bio TEXT,
            job_title TEXT,
            phone TEXT,
            avatar_url TEXT,
            profile_complete INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_name TEXT NOT NULL,
            github_url TEXT NOT NULL,
            linkedin_url TEXT NOT NULL,
            target_role TEXT NOT NULL,
            is_intern INTEGER NOT NULL,
            final_score REAL NOT NULL,
            data_completeness REAL NOT NULL,
            output_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            github_data_json TEXT,
            linkedin_data_json TEXT,
            pipeline_json TEXT,
            user_id INTEGER
        )
        """
    )
    _ensure_sqlite_user_profile_columns(conn)
    _ensure_sqlite_snapshot_columns(conn)


def _init_postgres(conn: _PgConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            bio TEXT,
            job_title TEXT,
            phone TEXT,
            avatar_url TEXT,
            profile_complete INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluations (
            id SERIAL PRIMARY KEY,
            candidate_name TEXT NOT NULL,
            github_url TEXT NOT NULL,
            linkedin_url TEXT NOT NULL,
            target_role TEXT NOT NULL,
            is_intern INTEGER NOT NULL,
            final_score DOUBLE PRECISION NOT NULL,
            data_completeness DOUBLE PRECISION NOT NULL,
            output_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            github_data_json TEXT,
            linkedin_data_json TEXT,
            pipeline_json TEXT,
            user_id INTEGER
        )
        """
    )
    _ensure_pg_user_profile_columns(conn)
    _ensure_pg_snapshot_columns(conn)


def init_db() -> None:
    with get_conn() as conn:
        if USE_POSTGRES:
            assert isinstance(conn, _PgConnection)
            _init_postgres(conn)
        else:
            assert isinstance(conn, sqlite3.Connection)
            _init_sqlite(conn)
        conn.commit()
