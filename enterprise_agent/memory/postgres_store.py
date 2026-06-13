"""PostgreSQL-backed session memory for deployed environments."""

from __future__ import annotations

import json
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from enterprise_agent.memory.models import Message, Session, Summary, utc_now


class PostgresMemoryStore:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database_url is required")
        self.database_url = database_url
        self._migrate()

    def _connect(self):
        return psycopg.connect(
            self.database_url,
            autocommit=False,
            row_factory=dict_row,
        )

    def _migrate(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        user_id TEXT NOT NULL,
                        thread_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        summary_version INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (user_id, thread_id)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        thread_id TEXT NOT NULL,
                        seq INTEGER NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        token_count INTEGER NOT NULL,
                        estimated BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL,
                        UNIQUE (user_id, thread_id, seq),
                        FOREIGN KEY (user_id, thread_id)
                            REFERENCES sessions(user_id, thread_id)
                            ON DELETE CASCADE
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS summaries (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        thread_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        covered_until_seq INTEGER NOT NULL,
                        content_json JSONB NOT NULL,
                        model TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        UNIQUE (user_id, thread_id, version),
                        FOREIGN KEY (user_id, thread_id)
                            REFERENCES sessions(user_id, thread_id)
                            ON DELETE CASCADE
                    )
                    """
                )

    def create_or_touch_session(self, user_id: str, thread_id: str) -> Session:
        _validate_identity(user_id, thread_id)
        now = utc_now()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sessions (
                        user_id, thread_id, created_at, updated_at, summary_version
                    ) VALUES (%s, %s, %s, %s, 0)
                    ON CONFLICT (user_id, thread_id)
                    DO UPDATE SET updated_at = EXCLUDED.updated_at
                    RETURNING user_id, thread_id, created_at, updated_at,
                              summary_version
                    """,
                    (user_id, thread_id, now, now),
                )
                row = cursor.fetchone()
        return _session_from_row(row)

    def append_message(
        self, user_id: str, thread_id: str, message: Message
    ) -> Message:
        self.create_or_touch_session(user_id, thread_id)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id FROM sessions
                    WHERE user_id = %s AND thread_id = %s
                    FOR UPDATE
                    """,
                    (user_id, thread_id),
                )
                cursor.execute(
                    """
                    SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq
                    FROM messages
                    WHERE user_id = %s AND thread_id = %s
                    """,
                    (user_id, thread_id),
                )
                seq = int(cursor.fetchone()["next_seq"])
                cursor.execute(
                    """
                    INSERT INTO messages (
                        user_id, thread_id, seq, role, content, token_count,
                        estimated, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        thread_id,
                        seq,
                        message.role,
                        message.content,
                        message.token_count,
                        message.estimated,
                        message.created_at,
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
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT seq, role, content, token_count, estimated, created_at
                    FROM messages
                    WHERE user_id = %s AND thread_id = %s
                    ORDER BY seq
                    """,
                    (user_id, thread_id),
                )
                rows = cursor.fetchall()
        return [
            Message(
                seq=int(row["seq"]),
                role=row["role"],
                content=row["content"],
                token_count=int(row["token_count"]),
                estimated=bool(row["estimated"]),
                created_at=_as_datetime(row["created_at"]),
            )
            for row in rows
        ]

    def get_summary(self, user_id: str, thread_id: str) -> Summary | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT version, covered_until_seq, content_json, model, created_at
                    FROM summaries
                    WHERE user_id = %s AND thread_id = %s
                    ORDER BY version DESC LIMIT 1
                    """,
                    (user_id, thread_id),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        content = row["content_json"]
        if isinstance(content, str):
            content = json.loads(content)
        return Summary(
            version=int(row["version"]),
            covered_until_seq=int(row["covered_until_seq"]),
            content=content,
            model=row["model"],
            created_at=_as_datetime(row["created_at"]),
        )

    def save_summary(
        self, user_id: str, thread_id: str, summary: Summary
    ) -> None:
        self.create_or_touch_session(user_id, thread_id)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO summaries (
                        user_id, thread_id, version, covered_until_seq,
                        content_json, model, created_at
                    ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (user_id, thread_id, version)
                    DO UPDATE SET
                        covered_until_seq = EXCLUDED.covered_until_seq,
                        content_json = EXCLUDED.content_json,
                        model = EXCLUDED.model,
                        created_at = EXCLUDED.created_at
                    """,
                    (
                        user_id,
                        thread_id,
                        summary.version,
                        summary.covered_until_seq,
                        json.dumps(summary.content, ensure_ascii=False),
                        summary.model,
                        summary.created_at,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE sessions
                    SET summary_version = %s, updated_at = %s
                    WHERE user_id = %s AND thread_id = %s
                    """,
                    (summary.version, utc_now(), user_id, thread_id),
                )

    def list_sessions(self, user_id: str) -> list[Session]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id, thread_id, created_at, updated_at,
                           summary_version
                    FROM sessions WHERE user_id = %s
                    ORDER BY updated_at DESC
                    """,
                    (user_id,),
                )
                rows = cursor.fetchall()
        return [_session_from_row(row) for row in rows]

    def delete_session(self, user_id: str, thread_id: str) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM sessions
                    WHERE user_id = %s AND thread_id = %s
                    """,
                    (user_id, thread_id),
                )


def _validate_identity(user_id: str, thread_id: str) -> None:
    if not user_id.strip() or not thread_id.strip():
        raise ValueError("user_id and thread_id are required")


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _session_from_row(row: dict) -> Session:
    return Session(
        user_id=row["user_id"],
        thread_id=row["thread_id"],
        created_at=_as_datetime(row["created_at"]),
        updated_at=_as_datetime(row["updated_at"]),
        summary_version=int(row["summary_version"]),
    )
