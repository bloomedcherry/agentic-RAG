"""Per-session execution locks."""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Iterator

import psycopg


class SessionConflictError(RuntimeError):
    error_type = "session_conflict"


class SessionLockManager:
    def __init__(self) -> None:
        self._locks: dict[tuple[str, str], threading.Lock] = {}
        self._guard = threading.Lock()

    @contextmanager
    def acquire(
        self, user_id: str, thread_id: str, *, timeout: float
    ) -> Iterator[None]:
        key = (user_id, thread_id)
        with self._guard:
            lock = self._locks.setdefault(key, threading.Lock())
        acquired = lock.acquire(timeout=timeout)
        if not acquired:
            raise SessionConflictError(
                f"session {user_id}:{thread_id} is already running"
            )
        try:
            yield
        finally:
            lock.release()


DEFAULT_SESSION_LOCK_MANAGER = SessionLockManager()


class PostgresSessionLockManager:
    def __init__(self, database_url: str, poll_interval: float = 0.05) -> None:
        self.database_url = database_url
        self.poll_interval = poll_interval

    @contextmanager
    def acquire(
        self, user_id: str, thread_id: str, *, timeout: float
    ) -> Iterator[None]:
        lock_id = _advisory_lock_id(user_id, thread_id)
        connection = psycopg.connect(self.database_url, autocommit=True)
        deadline = time.monotonic() + timeout
        acquired = False
        try:
            while time.monotonic() < deadline:
                acquired = bool(
                    connection.execute(
                        "SELECT pg_try_advisory_lock(%s)",
                        (lock_id,),
                    ).fetchone()[0]
                )
                if acquired:
                    break
                time.sleep(self.poll_interval)
            if not acquired:
                raise SessionConflictError(
                    f"session {user_id}:{thread_id} is already running"
                )
            yield
        finally:
            if acquired:
                connection.execute(
                    "SELECT pg_advisory_unlock(%s)",
                    (lock_id,),
                )
            connection.close()


def _advisory_lock_id(user_id: str, thread_id: str) -> int:
    import hashlib

    raw = hashlib.sha256(f"{user_id}:{thread_id}".encode()).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)
