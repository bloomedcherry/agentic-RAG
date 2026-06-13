from __future__ import annotations

import os

import pytest

from enterprise_agent.memory.models import Message, Summary
from enterprise_agent.memory.postgres_store import PostgresMemoryStore


@pytest.mark.skipif(
    not os.getenv("TEST_MEMORY_POSTGRES_URL"),
    reason="TEST_MEMORY_POSTGRES_URL is not configured",
)
def test_postgres_store_contract() -> None:
    store = PostgresMemoryStore(os.environ["TEST_MEMORY_POSTGRES_URL"])
    user_id = "m6-integration-user"
    thread_id = "m6-integration-thread"
    store.delete_session(user_id, thread_id)

    store.append_message(
        user_id,
        thread_id,
        Message(role="user", content="测试 PostgreSQL Memory", token_count=5),
    )
    store.save_summary(
        user_id,
        thread_id,
        Summary(
            version=1,
            covered_until_seq=1,
            content={"facts": ["PostgreSQL Memory 可用"]},
            model="integration-test",
        ),
    )

    assert store.list_messages(user_id, thread_id)[0].content == "测试 PostgreSQL Memory"
    assert store.get_summary(user_id, thread_id).version == 1

    store.delete_session(user_id, thread_id)
    assert store.list_messages(user_id, thread_id) == []
