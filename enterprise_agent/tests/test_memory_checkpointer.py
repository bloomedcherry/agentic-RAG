from __future__ import annotations

from langgraph.checkpoint.sqlite import SqliteSaver

from enterprise_agent.config import Settings
from enterprise_agent.memory import checkpointer
from enterprise_agent.memory.checkpointer import build_checkpointer, checkpoint_thread_key


def test_sqlite_checkpointer_factory_and_safe_thread_key(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        memory_backend="sqlite",
        memory_sqlite_path=str(tmp_path / "memory.db"),
    )

    saver = build_checkpointer(settings)

    assert isinstance(saver, SqliteSaver)
    assert checkpoint_thread_key("user-1", "thread") != checkpoint_thread_key(
        "user-2", "thread"
    )
    assert checkpoint_thread_key("user-1", "thread") == checkpoint_thread_key(
        "user-1", "thread"
    )


def test_postgres_checkpointer_factory(monkeypatch) -> None:
    connection = object()

    class FakePostgresSaver:
        def __init__(self, received_connection):
            assert received_connection is connection
            self.setup_called = False

        def setup(self):
            self.setup_called = True

    monkeypatch.setattr(checkpointer.psycopg, "connect", lambda *args, **kwargs: connection)
    monkeypatch.setattr(checkpointer, "PostgresSaver", FakePostgresSaver)
    settings = Settings(
        _env_file=None,
        memory_backend="postgres",
        memory_postgres_url="postgresql://example/test",
    )

    saver = build_checkpointer(settings)

    assert isinstance(saver, FakePostgresSaver)
    assert saver.setup_called is True
