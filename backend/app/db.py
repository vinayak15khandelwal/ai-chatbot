"""SQLite persistence (stdlib sqlite3, one short-lived connection per operation)."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, id);
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    system_prompt TEXT,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sqlite_path(database_url: str) -> str:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("DATABASE_URL must look like sqlite:////data/app.db")
    return database_url[len(prefix):]


class Database:
    def __init__(self, database_url: str):
        self.path = sqlite_path(database_url)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:  # commit on success, rollback on error
                yield conn
        finally:
            conn.close()

    def init(self) -> None:
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        with self._conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(SCHEMA)

    def ping(self) -> bool:
        try:
            with self._conn() as c:
                c.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def session_exists(self, session_id: str) -> bool:
        with self._conn() as c:
            return c.execute("SELECT 1 FROM sessions WHERE session_id=?", (session_id,)).fetchone() is not None

    def get_system_prompt(self, session_id: str) -> Optional[str]:
        with self._conn() as c:
            row = c.execute("SELECT system_prompt FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        return row["system_prompt"] if row else None

    def get_history(self, session_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT role, content, metadata FROM messages WHERE session_id=? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        out = []
        for r in rows:
            item = {"role": r["role"], "content": r["content"]}
            if r["role"] == "assistant" and r["metadata"]:
                item["metadata"] = json.loads(r["metadata"])
            out.append(item)
        return out

    def save_exchange(
        self, session_id: str, system_prompt: Optional[str], user_content: str, reply: str, metadata: dict
    ) -> None:
        """Atomically store the session row and both messages (only called after a successful LLM reply)."""
        with self._conn() as c:
            existing = c.execute("SELECT 1 FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            if existing is None:
                c.execute(
                    "INSERT INTO sessions (session_id, system_prompt, created_at) VALUES (?,?,?)",
                    (session_id, system_prompt, _now()),
                )
            elif system_prompt is not None:
                c.execute("UPDATE sessions SET system_prompt=? WHERE session_id=?", (system_prompt, session_id))
            c.execute(
                "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?,?,?,?,?)",
                (session_id, "user", user_content, None, _now()),
            )
            c.execute(
                "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?,?,?,?,?)",
                (session_id, "assistant", reply, json.dumps(metadata), _now()),
            )
