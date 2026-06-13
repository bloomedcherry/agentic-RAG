"""SQLite-backed session memory for local development."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from enterprise_agent.memory.models import Message, Session, Summary, utc_now


class SQLiteMemoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    summary_version INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, thread_id)
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    estimated INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    UNIQUE (user_id, thread_id, seq),
                    FOREIGN KEY (user_id, thread_id)
                        REFERENCES sessions(user_id, thread_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    covered_until_seq INTEGER NOT NULL,
                    content_json TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (user_id, thread_id, version),
                    FOREIGN KEY (user_id, thread_id)
                        REFERENCES sessions(user_id, thread_id)
                        ON DELETE CASCADE
                );
                """
            )

    def create_or_touch_session(self, user_id: str, thread_id: str) -> Session:
        _validate_identity(user_id, thread_id)
        now = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    user_id, thread_id, created_at, updated_at, summary_version
                ) VALUES (?, ?, ?, ?, 0)
                ON CONFLICT(user_id, thread_id)
                DO UPDATE SET updated_at = excluded.updated_at
                """,
                (user_id, thread_id, now, now),
            )
            row = connection.execute(
                """
                SELECT user_id, thread_id, created_at, updated_at, summary_version
                FROM sessions WHERE user_id = ? AND thread_id = ?
                """,
                (user_id, thread_id),
            ).fetchone()
        return _session_from_row(row)

    def append_message(
        self, user_id: str, thread_id: str, message: Message
    ) -> Message:
        self.create_or_touch_session(user_id, thread_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq
                FROM messages WHERE user_id = ? AND thread_id = ?
                """,
                (user_id, thread_id),
            ).fetchone()
            seq = int(row["next_seq"])
            connection.execute(
                """
                INSERT INTO messages (
                    user_id, thread_id, seq, role, content, token_count,
                    estimated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    thread_id,
                    seq,
                    message.role,
                    message.content,
                    message.token_count,
                    int(message.estimated),
                    message.created_at.isoformat(),
                ),
            )
        return Message(
            role=message.role,
            content=message.content,
            token_count=message.token_count,
            seq=seq,
            created_at=message.created_at,
            estimated=message.estimated,
        )

    def list_messages(self, user_id: str, thread_id: str) -> list[Message]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT seq, role, content, token_count, estimated, created_at
                FROM messages
                WHERE user_id = ? AND thread_id = ?
                ORDER BY seq
                """,
                (user_id, thread_id),
            ).fetchall()
        return [
            Message(
                seq=int(row["seq"]),
                role=row["role"],
                content=row["content"],
                token_count=int(row["token_count"]),
                estimated=bool(row["estimated"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def get_summary(self, user_id: str, thread_id: str) -> Summary | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT version, covered_until_seq, content_json, model, created_at
                FROM summaries
                WHERE user_id = ? AND thread_id = ?
                ORDER BY version DESC LIMIT 1
                """,
                (user_id, thread_id),
            ).fetchone()
        if row is None:
            return None
        return Summary(
            version=int(row["version"]),
            covered_until_seq=int(row["covered_until_seq"]),
            content=json.loads(row["content_json"]),
            model=row["model"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def save_summary(
        self, user_id: str, thread_id: str, summary: Summary
    ) -> None:
        self.create_or_touch_session(user_id, thread_id)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO summaries (
                    user_id, thread_id, version, covered_until_seq,
                    content_json, model, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, thread_id, version)
                DO UPDATE SET
                    covered_until_seq = excluded.covered_until_seq,
                    content_json = excluded.content_json,
                    model = excluded.model,
                    created_at = excluded.created_at
                """,
                (
                    user_id,
                    thread_id,
                    summary.version,
                    summary.covered_until_seq,
                    json.dumps(summary.content, ensure_ascii=False),
                    summary.model,
                    summary.created_at.isoformat(),
                ),
            )
            connection.execute(
                """
                UPDATE sessions SET summary_version = ?, updated_at = ?
                WHERE user_id = ? AND thread_id = ?
                """,
                (
                    summary.version,
                    utc_now().isoformat(),
                    user_id,
                    thread_id,
                ),
            )

    def list_sessions(self, user_id: str) -> list[Session]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT user_id, thread_id, created_at, updated_at, summary_version
                FROM sessions WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [_session_from_row(row) for row in rows]

    def delete_session(self, user_id: str, thread_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE user_id = ? AND thread_id = ?",
                (user_id, thread_id),
            )


def _validate_identity(user_id: str, thread_id: str) -> None:
    if not user_id.strip() or not thread_id.strip():
        raise ValueError("user_id and thread_id are required")


def _session_from_row(row: sqlite3.Row) -> Session:
    return Session(
        user_id=row["user_id"],
        thread_id=row["thread_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        summary_version=int(row["summary_version"]),
    )
