"""SQLite-backed set of already-seen job IDs, so overlapping poll windows
never produce duplicate Excel rows, and this survives script restarts."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL
            )
            """
        )


def has_seen(job_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None


def mark_seen(job_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_jobs (job_id, first_seen_at) VALUES (?, ?)",
            (job_id, datetime.now(timezone.utc).isoformat()),
        )


@contextmanager
def _connect():
    conn = sqlite3.connect(str(config.DEDUP_DB_PATH))
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
