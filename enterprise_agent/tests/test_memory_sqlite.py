from __future__ import annotations

from enterprise_agent.memory.models import Message, Summary
from enterprise_agent.memory.sqlite_store import SQLiteMemoryStore


def test_sqlite_store_persists_messages_and_updates_summary(tmp_path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.db")

    session = store.create_or_touch_session("user-1", "thread-1")
    store.append_message(
        "user-1",
        "thread-1",
        Message(role="user", content="分析 A 项目风险", token_count=8),
    )
    store.append_message(
        "user-1",
        "thread-1",
        Message(role="assistant", content="存在预算和交付风险", token_count=10),
    )
    store.save_summary(
        "user-1",
        "thread-1",
        Summary(
            version=1,
            covered_until_seq=2,
            content={"facts": ["A 项目存在预算和交付风险"]},
            model="test-model",
        ),
    )
    store.save_summary(
        "user-1",
        "thread-1",
        Summary(
            version=2,
            covered_until_seq=2,
            content={"facts": ["A 项目存在两个风险"], "referents": {"第二个风险": "交付风险"}},
            model="test-model",
        ),
    )

    messages = store.list_messages("user-1", "thread-1")
    summary = store.get_summary("user-1", "thread-1")

    assert session.user_id == "user-1"
    assert [message.seq for message in messages] == [1, 2]
    assert [message.role for message in messages] == ["user", "assistant"]
    assert summary is not None
    assert summary.version == 2
    assert summary.content["referents"]["第二个风险"] == "交付风险"


def test_sqlite_store_isolates_users_and_cascades_session_delete(tmp_path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    for user_id, content in (("user-1", "用户一"), ("user-2", "用户二")):
        store.append_message(
            user_id,
            "shared-thread",
            Message(role="user", content=content, token_count=2),
        )
        store.save_summary(
            user_id,
            "shared-thread",
            Summary(
                version=1,
                covered_until_seq=1,
                content={"facts": [content]},
                model="test-model",
            ),
        )

    store.delete_session("user-1", "shared-thread")

    assert store.list_messages("user-1", "shared-thread") == []
    assert store.get_summary("user-1", "shared-thread") is None
    assert [message.content for message in store.list_messages("user-2", "shared-thread")] == [
        "用户二"
    ]
    assert [session.thread_id for session in store.list_sessions("user-2")] == [
        "shared-thread"
    ]
