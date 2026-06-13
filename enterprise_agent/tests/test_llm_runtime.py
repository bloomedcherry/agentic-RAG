"""Integration tests for LLM planning and answer generation."""

from __future__ import annotations

from enterprise_agent.agent.answer_generator import AnswerGenerator
from enterprise_agent.agent.context_builder import ContextBuilder
from enterprise_agent.agent.runtime import Runtime
from enterprise_agent.llm.fake import FakeLLMClient
from enterprise_agent.tests.test_runtime import _prepare_runtime_data


def _policy_planner() -> FakeLLMClient:
    return FakeLLMClient(
        parsed={
            "task_type": "policy_qa",
            "plan": ["检索制度", "根据证据回答"],
            "selected_tools": ["search_kb"],
            "reason": "用户询问差旅制度",
        },
        model="fake-planner",
    )


def test_llm_answer_is_used_and_keeps_retrieval_source(tmp_path) -> None:
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    answer_llm = FakeLLMClient(
        content="结论：需要发票、行程单、审批单和费用明细。\n来源：travel.md",
        model="fake-answer",
    )

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        trace_path=tmp_path / "trace.jsonl",
        planner_llm_client=_policy_planner(),
        answer_llm_client=answer_llm,
    ).run("差旅报销需要哪些材料？", user_role="employee")

    assert result["answer"].startswith("结论：需要发票")
    assert "来源：travel.md" in result["answer"]
    assert result["verifier_result"]["pass"] is True
    assert [call["purpose"] for call in result["llm_calls"]] == [
        "planner",
        "answer_generator",
    ]
    assert answer_llm.call_count == 1


def test_llm_answer_without_citation_is_caught_by_verifier(tmp_path) -> None:
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    answer_llm = FakeLLMClient(content="结论：需要提交发票。")

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        trace_path=tmp_path / "trace.jsonl",
        planner_llm_client=_policy_planner(),
        answer_llm_client=answer_llm,
    ).run("差旅报销需要哪些材料？", user_role="employee")

    assert result["verifier_history"][0]["pass"] is False
    assert result["verifier_history"][0]["issues"][0]["type"] == "missing_citation"
    assert result["verifier_result"]["pass"] is True
    assert "来源：travel.md" in result["answer"]


def test_answer_model_failure_preserves_m4_template_behavior(tmp_path) -> None:
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    unavailable = FakeLLMClient(
        content="answer endpoint unavailable",
        status="error",
        error_type="llm_unavailable",
    )

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        trace_path=tmp_path / "trace.jsonl",
        answer_llm_client=unavailable,
    ).run("差旅报销需要哪些材料？", user_role="employee")

    assert "结论：差旅报销通常需要提交以下材料" in result["answer"]
    assert "来源：travel.md" in result["answer"]
    assert result["llm_fallback_used"] is True
    assert result["llm_calls"][0]["error_type"] == "llm_unavailable"


def test_permission_denial_does_not_call_answer_model(tmp_path) -> None:
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    planner_llm = FakeLLMClient(
        parsed={
            "task_type": "data_analysis",
            "plan": ["查询业务数据"],
            "selected_tools": ["query_sql", "generate_report"],
            "reason": "用户要求采购金额统计",
        }
    )
    answer_llm = FakeLLMClient(content="# 虚假的数据结论\n\n采购总额为一亿元。")

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        trace_path=tmp_path / "trace.jsonl",
        planner_llm_client=planner_llm,
        answer_llm_client=answer_llm,
    ).run("查询所有部门采购金额统计", user_role="employee")

    assert result["tool_calls"] == [{"name": "query_sql", "status": "permission_denied"}]
    assert answer_llm.call_count == 0
    assert result["answer"] == "拒绝执行：当前角色无权调用 query_sql"


def test_context_builder_bounds_llm_context_and_omits_derived_report() -> None:
    documents = [
        {
            "source": f"project_{index}.md",
            "content": f"项目证据 {index}：" + ("风险描述" * 500),
        }
        for index in range(5)
    ]
    state = ContextBuilder().build(
        {
            "query": "分析项目风险",
            "role": "manager",
            "task_type": "project_analysis",
            "retrieved_docs": documents,
            "tool_outputs": {
                "search_kb": {"documents": documents},
                "generate_report": {"markdown": "# 重复的派生报告\n" + ("重复" * 2000)},
            },
        }
    )

    assert len(state["context"]) <= 1200
    assert "project_0.md" in state["context"]
    assert "generate_report" not in state["context"]
    assert "重复的派生报告" not in state["context"]


def test_answer_generator_uses_configured_completion_budget() -> None:
    answer_llm = FakeLLMClient(content="结论：已回答。\n来源：policy.md")

    AnswerGenerator(answer_llm, max_tokens=4096).generate(
        {
            "query": "制度要求是什么？",
            "task_type": "policy_qa",
            "context": "来源：policy.md",
        }
    )

    assert answer_llm.requests[0].max_tokens == 4096


def test_context_builder_preserves_referents_from_recent_answer() -> None:
    second_risk = "第二个风险是报告频率不一致，应统一为周度报告。"
    state = ContextBuilder(max_context_chars=32_000).build(
        {
            "query": "第二个风险怎么处理？",
            "role": "manager",
            "task_type": "project_analysis",
            "memory_context": {
                "recent_messages": [
                    {
                        "role": "assistant",
                        "content": ("前置分析内容。" * 20) + second_risk,
                    }
                ]
            },
            "retrieved_docs": [],
            "tool_outputs": {},
        }
    )

    assert second_risk in state["context"]


def test_answer_generator_removes_model_reasoning_block() -> None:
    answer_llm = FakeLLMClient(
        content="<think>内部推理过程，不应展示。</think>\n结论：需要审批。\n来源：workflow.md"
    )

    answer, _ = AnswerGenerator(answer_llm).generate(
        {
            "query": "是否需要审批？",
            "task_type": "workflow_check",
            "context": "来源：workflow.md",
        }
    )

    assert answer == "结论：需要审批。\n来源：workflow.md"


def test_answer_prompt_requests_concise_final_output() -> None:
    answer_llm = FakeLLMClient(content="结论：已完成。\n来源：data.md")

    AnswerGenerator(answer_llm).generate(
        {
            "query": "统计高风险项目",
            "task_type": "data_analysis",
            "context": "来源：data.md",
        }
    )

    system_prompt = answer_llm.requests[0].messages[0]["content"]
    assert "final answer only" in system_prompt
    assert "at most 5" in system_prompt
