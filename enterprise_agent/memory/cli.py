"""CLI for inspecting and deleting session memory."""

from __future__ import annotations

import argparse

from enterprise_agent.config import Settings
from enterprise_agent.memory.base import MemoryStore
from enterprise_agent.memory.checkpointer import (
    build_checkpointer,
    checkpoint_thread_key,
)
from enterprise_agent.memory.sqlite_store import SQLiteMemoryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage enterprise agent sessions.")
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list")
    list_parser.add_argument("--user-id", required=True)

    show_parser = commands.add_parser("show")
    show_parser.add_argument("--user-id", required=True)
    show_parser.add_argument("--thread-id", required=True)

    delete_parser = commands.add_parser("delete")
    delete_parser.add_argument("--user-id", required=True)
    delete_parser.add_argument("--thread-id", required=True)
    delete_parser.add_argument("--yes", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    store = _build_store(Settings())

    if args.command == "list":
        sessions = store.list_sessions(args.user_id)
        for session in sessions:
            print(
                f"thread_id: {session.thread_id} "
                f"updated_at: {session.updated_at.isoformat()} "
                f"summary_version: {session.summary_version}"
            )
        return

    if args.command == "show":
        messages = store.list_messages(args.user_id, args.thread_id)
        summary = store.get_summary(args.user_id, args.thread_id)
        sessions = {
            session.thread_id: session
            for session in store.list_sessions(args.user_id)
        }
        session = sessions.get(args.thread_id)
        print(f"thread_id: {args.thread_id}")
        print(f"message_count: {len(messages)}")
        print(f"summary_version: {summary.version if summary else 0}")
        print(f"updated_at: {session.updated_at.isoformat() if session else ''}")
        print("recent_messages:")
        for message in messages[-10:]:
            content = " ".join(message.content.split())[:240]
            print(f"- {message.role}: {content}")
        return

    if not args.yes:
        parser.error("delete requires --yes")
    store.delete_session(args.user_id, args.thread_id)
    checkpointer = build_checkpointer(Settings())
    checkpointer.delete_thread(
        checkpoint_thread_key(args.user_id, args.thread_id)
    )
    print(f"deleted: {args.user_id}/{args.thread_id}")


def _build_store(settings: Settings) -> MemoryStore:
    if settings.memory_backend == "postgres":
        from enterprise_agent.memory.postgres_store import PostgresMemoryStore

        return PostgresMemoryStore(settings.memory_postgres_url or "")
    return SQLiteMemoryStore(settings.memory_sqlite_path)


if __name__ == "__main__":
    main()
