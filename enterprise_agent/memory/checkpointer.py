"""Factory for LangGraph checkpoint persistence."""

from __future__ import annotations

import hashlib
import sqlite3

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver

from enterprise_agent.config import Settings


def checkpoint_thread_key(user_id: str, thread_id: str) -> str:
    return hashlib.sha256(f"{user_id}:{thread_id}".encode()).hexdigest()


def build_checkpointer(settings: Settings):
    if settings.memory_backend == "postgres":
        connection = psycopg.connect(
            settings.memory_postgres_url,
            autocommit=True,
            prepare_threshold=0,
        )
        saver = PostgresSaver(connection)
    else:
        connection = sqlite3.connect(
            settings.memory_sqlite_path,
            check_same_thread=False,
        )
        saver = SqliteSaver(connection)
    saver.setup()
    return saver
