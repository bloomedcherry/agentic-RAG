from __future__ import annotations

from enterprise_agent.llm.fake import FakeLLMClient
from enterprise_agent.memory.manager import MemoryManager
from enterprise_agent.memory.models import Message
from enterprise_agent.memory.sqlite_store import SQLiteMemoryStore
from enterprise_agent.memory.summarizer import MemorySummarizer


def _append_turns(store, count: int, *, tokens_per_message: int = 2) -> None:
    for index in range(count):
        store.append_message(
            "user-1",
            "thread-1",
            Message(
                role="user",
                content=f"问题 {index + 1}",
                token_count=tokens_per_message,
            ),
        )
        store.append_message(
            "user-1",
            "thread-1",
            Message(
                role="assistant",
                content=f"回答 {index + 1}",
                token_count=tokens_per_message,
            ),
        )


def test_memory_context_keeps_recent_turns_without_summary(tmp_path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    _append_turns(store, 3)
    manager = MemoryManager(store, max_recent_turns=10, max_context_tokens=100)

    context = manager.load_context("user-1", "thread-1")

    assert len(context["recent_messages"]) == 6
    assert context["summary"] is None
    assert context["needs_summary"] is False
    assert context["total_tokens"] == 12


def test_memory_context_summarizes_messages_outside_turn_window(tmp_path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    _append_turns(store, 12)
    fake = FakeLLMClient(
        parsed={
            "facts": ["A 项目有预算风险和交付风险"],
            "decisions": [],
            "open_items": [],
            "referents": {"第二个风险": "交付风险"},
        }
    )
    manager = MemoryManager(
        store,
        summarizer=MemorySummarizer(fake),
        max_recent_turns=10,
        max_context_tokens=1000,
    )

    before = manager.load_context("user-1", "thread-1")
    summary = manager.summarize_if_needed("user-1", "thread-1", before)
    after = manager.load_context("user-1", "thread-1")

    assert before["needs_summary"] is True
    assert summary is not None
    assert summary.covered_until_seq == 4
    assert after["summary"]["referents"]["第二个风险"] == "交付风险"
    assert len(after["recent_messages"]) == 20


def test_token_limit_triggers_early_summary_and_failure_keeps_history(tmp_path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    _append_turns(store, 3, tokens_per_message=30)
    fake = FakeLLMClient(status="error", error_type="llm_unavailable")
    manager = MemoryManager(
        store,
        summarizer=MemorySummarizer(fake),
        max_recent_turns=10,
        max_context_tokens=100,
    )

    context = manager.load_context("user-1", "thread-1")
    summary = manager.summarize_if_needed("user-1", "thread-1", context)

    assert context["needs_summary"] is True
    assert context["total_tokens"] <= 100
    assert summary is None
    assert len(store.list_messages("user-1", "thread-1")) == 6
    assert store.get_summary("user-1", "thread-1") is None


def test_new_summary_is_incremental_from_previous_summary(tmp_path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    fake = FakeLLMClient(
        parsed={
            "facts": ["第一阶段风险"],
            "decisions": [],
            "open_items": [],
            "referents": {},
        }
    )
    manager = MemoryManager(
        store,
        summarizer=MemorySummarizer(fake),
        max_recent_turns=1,
        max_context_tokens=1000,
    )
    _append_turns(store, 2)
    manager.summarize_if_needed(
        "user-1", "thread-1", manager.load_context("user-1", "thread-1")
    )
    _append_turns(store, 1)
    fake.response.parsed = {
        "facts": ["第一阶段风险", "第二阶段风险"],
        "decisions": [],
        "open_items": [],
        "referents": {},
    }

    manager.summarize_if_needed(
        "user-1", "thread-1", manager.load_context("user-1", "thread-1")
    )

    assert fake.call_count == 2
    second_payload = fake.requests[1].messages[1]["content"]
    assert "第一阶段风险" in second_payload
    assert store.get_summary("user-1", "thread-1").version == 2
