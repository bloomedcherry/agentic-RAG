from __future__ import annotations

import os
import subprocess
import sys

from enterprise_agent.app import build_parser
from enterprise_agent.memory.models import Message
from enterprise_agent.memory.sqlite_store import SQLiteMemoryStore


def _run_memory_cli(db_path, *args):
    environment = os.environ.copy()
    environment.update(
        {
            "MEMORY_BACKEND": "sqlite",
            "MEMORY_SQLITE_PATH": str(db_path),
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "enterprise_agent.memory.cli", *args],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_agent_cli_accepts_explicit_session_identifiers() -> None:
    args = build_parser().parse_args(
        [
            "--query",
            "test",
            "--user-id",
            "user-1",
            "--thread-id",
            "thread-1",
        ]
    )

    assert args.user_id == "user-1"
    assert args.thread_id == "thread-1"


def test_memory_cli_lists_shows_and_deletes_session(tmp_path) -> None:
    db_path = tmp_path / "memory.db"
    store = SQLiteMemoryStore(db_path)
    store.append_message(
        "user-1",
        "thread-1",
        Message(role="user", content="第一轮问题", token_count=3),
    )

    listed = _run_memory_cli(db_path, "list", "--user-id", "user-1")
    shown = _run_memory_cli(
        db_path,
        "show",
        "--user-id",
        "user-1",
        "--thread-id",
        "thread-1",
    )
    rejected = _run_memory_cli(
        db_path,
        "delete",
        "--user-id",
        "user-1",
        "--thread-id",
        "thread-1",
    )
    deleted = _run_memory_cli(
        db_path,
        "delete",
        "--user-id",
        "user-1",
        "--thread-id",
        "thread-1",
        "--yes",
    )

    assert listed.returncode == 0
    assert "thread-1" in listed.stdout
    assert shown.returncode == 0
    assert "message_count: 1" in shown.stdout
    assert "第一轮问题" in shown.stdout
    assert rejected.returncode != 0
    assert deleted.returncode == 0
    assert store.list_sessions("user-1") == []
