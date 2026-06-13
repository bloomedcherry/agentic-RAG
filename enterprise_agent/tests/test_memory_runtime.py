from __future__ import annotations

from enterprise_agent.agent.runtime import Runtime
from enterprise_agent.config import Settings
from enterprise_agent.llm.fake import FakeLLMClient
from enterprise_agent.memory.sqlite_store import SQLiteMemoryStore
from enterprise_agent.tests.test_runtime import _prepare_runtime_data


def _settings(tmp_path):
    return Settings(
        _env_file=None,
        llm_enabled=False,
        memory_backend="sqlite",
        memory_sqlite_path=str(tmp_path / "memory.db"),
    )


def test_runtime_restores_same_session_after_runtime_rebuild(tmp_path) -> None:
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    first_llm = FakeLLMClient(content="# A 项目风险\n\n1. 预算风险\n2. 交付风险")
    first = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        settings=_settings(tmp_path),
        answer_llm_client=first_llm,
    ).run(
        "帮我分析 A 项目风险",
        user_role="manager",
        user_id="user-1",
        thread_id="project-a",
    )

    second_llm = FakeLLMClient(content="第二个风险是交付风险，建议跟踪供应商里程碑。")
    second = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        settings=_settings(tmp_path),
        answer_llm_client=second_llm,
    ).run(
        "第二个风险怎么处理？",
        user_role="manager",
        user_id="user-1",
        thread_id="project-a",
    )

    assert first["thread_id"] == "project-a"
    assert second["answer"].startswith("第二个风险是交付风险")
    assert "帮我分析 A 项目风险" in second_llm.requests[0].messages[1]["content"]
    assert "# A 项目风险" in second_llm.requests[0].messages[1]["content"]


def test_runtime_isolates_threads_and_users(tmp_path) -> None:
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    runtime = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        settings=_settings(tmp_path),
        answer_llm_client=FakeLLMClient(content="第一轮答案"),
    )
    runtime.run(
        "第一轮秘密内容",
        user_role="manager",
        user_id="user-1",
        thread_id="thread-1",
    )

    for user_id, thread_id in (
        ("user-1", "thread-2"),
        ("user-2", "thread-1"),
    ):
        llm = FakeLLMClient(content="隔离答案")
        Runtime(
            index_dir=index_dir,
            db_path=db_path,
            workflow_rules_path=rules_path,
            settings=_settings(tmp_path),
            answer_llm_client=llm,
        ).run(
            "新的问题",
            user_role="manager",
            user_id=user_id,
            thread_id=thread_id,
        )
        assert "第一轮秘密内容" not in llm.requests[0].messages[1]["content"]


def test_memory_write_failure_does_not_discard_answer(tmp_path) -> None:
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)

    class FailingStore(SQLiteMemoryStore):
        def append_message(self, user_id, thread_id, message):
            raise OSError("disk unavailable")

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        settings=_settings(tmp_path),
        memory_store=FailingStore(tmp_path / "failing.db"),
        answer_llm_client=FakeLLMClient(content="仍然返回的答案"),
    ).run(
        "差旅报销需要哪些材料？",
        user_role="employee",
        user_id="user-1",
        thread_id="thread-1",
    )

    assert result["answer"].startswith("仍然返回的答案")
    assert any(error["type"] == "memory_write_error" for error in result["errors"])


def test_runtime_generates_session_identifiers_when_omitted(tmp_path) -> None:
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        settings=_settings(tmp_path),
        llm_enabled=False,
    ).run("差旅报销需要哪些材料？")

    assert result["user_id"]
    assert result["thread_id"]
