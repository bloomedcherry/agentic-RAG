"""Tests for LLM planning and deterministic rule fallback."""

from __future__ import annotations

from enterprise_agent.agent.permission import check_permission
from enterprise_agent.agent.planner import Planner
from enterprise_agent.agent.router import Router
from enterprise_agent.llm.fake import FakeLLMClient
from enterprise_agent.tools.registry import ToolRegistry
from enterprise_agent.tools.runtime_tools import QuerySqlTool, SearchKbTool


def _metadata() -> list[dict]:
    return [
        {"name": "search_kb", "description": "Search knowledge"},
        {"name": "query_sql", "description": "Query controlled business data"},
        {"name": "generate_report", "description": "Generate a report"},
        {"name": "workflow_check", "description": "Check workflow rules"},
    ]


def test_valid_llm_plan_overrides_rule_planner() -> None:
    llm = FakeLLMClient(
        parsed={
            "task_type": "project_analysis",
            "plan": ["查找项目证据", "整理风险"],
            "selected_tools": ["search_kb", "generate_report"],
            "reason": "需要分析项目风险",
        }
    )

    planned = Planner(llm_client=llm, tool_metadata_provider=_metadata).plan(
        {"query": "请整理交付情况", "role": "manager"}
    )

    assert planned["task_type"] == "project_analysis"
    assert planned["plan"] == ["查找项目证据", "整理风险"]
    assert planned["selected_tools"] == ["search_kb", "generate_report"]
    assert planned["planner_source"] == "llm"
    assert Router().route(planned)["selected_tools"] == ["search_kb", "generate_report"]


def test_unknown_tool_rejects_llm_output_and_uses_rule_plan() -> None:
    llm = FakeLLMClient(
        parsed={
            "task_type": "data_analysis",
            "plan": ["执行任意命令"],
            "selected_tools": ["shell_exec"],
            "reason": "模型选择了未注册工具",
        }
    )

    planned = Planner(llm_client=llm, tool_metadata_provider=_metadata).plan(
        {"query": "差旅报销需要哪些材料？", "role": "employee"}
    )

    assert planned["task_type"] == "policy_qa"
    assert planned["selected_tools"] == ["search_kb"]
    assert planned["planner_source"] == "rule"
    assert planned["llm_fallback_used"] is True
    assert planned["llm_calls"][0]["error_type"] == "llm_invalid_output"


def test_unavailable_llm_matches_existing_rule_planner() -> None:
    state = {"query": "统计当前高风险项目", "role": "manager"}
    expected = Planner().plan(state)
    unavailable = FakeLLMClient(
        content="service unavailable",
        status="error",
        error_type="llm_unavailable",
    )

    planned = Planner(llm_client=unavailable, tool_metadata_provider=_metadata).plan(state)

    assert planned["task_type"] == expected["task_type"]
    assert planned["plan"] == expected["plan"]
    assert planned["selected_tools"] == expected["selected_tools"]
    assert planned["llm_fallback_used"] is True


def test_llm_plan_cannot_bypass_role_permission() -> None:
    llm = FakeLLMClient(
        parsed={
            "task_type": "data_analysis",
            "plan": ["查询业务数据"],
            "selected_tools": ["query_sql"],
            "reason": "需要统计业务数据",
        }
    )
    registry = ToolRegistry()
    registry.register(SearchKbTool())
    registry.register(QuerySqlTool())

    planned = Planner(llm_client=llm, tool_metadata_provider=registry.list_metadata).plan(
        {"query": "查询所有部门采购金额", "role": "employee"}
    )
    routed = Router().route(planned)
    permission = check_permission("employee", registry.get(routed["selected_tools"][0]))

    assert routed["selected_tools"] == ["query_sql"]
    assert permission["allowed"] is False
    assert permission["error_type"] == "permission_denied"
