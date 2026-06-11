"""LLM-backed planner with deterministic rule fallback."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from enterprise_agent.agent.state import AgentState
from enterprise_agent.llm.base import BaseLLMClient, LLMRequest, llm_call_summary
from enterprise_agent.llm.prompts import PLANNER_PROMPT_VERSION, build_planner_messages
from enterprise_agent.llm.schemas import PlannerDecision

DEFAULT_TOOL_METADATA = [
    {"name": "search_kb", "description": "Search the enterprise knowledge base"},
    {"name": "workflow_check", "description": "Check configured workflow rules"},
    {"name": "query_sql", "description": "Run controlled business data queries"},
    {"name": "generate_report", "description": "Generate a Markdown report"},
]


class Planner:
    PLANS = {
        "policy_qa": ["检索知识库", "基于来源生成制度问答"],
        "workflow_check": ["检索知识库", "读取流程规则", "判断是否需要审批"],
        "project_analysis": ["检索知识库", "生成项目分析草稿"],
        "data_analysis": ["查询业务数据", "生成数据分析草稿"],
    }
    TOOLS = {
        "policy_qa": ["search_kb"],
        "workflow_check": ["search_kb", "workflow_check"],
        "project_analysis": ["search_kb", "generate_report"],
        "data_analysis": ["query_sql", "generate_report"],
    }

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        tool_metadata_provider: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.tool_metadata_provider = tool_metadata_provider

    def plan(self, state: AgentState) -> AgentState:
        if self.llm_client is not None:
            return self._plan_with_llm(state)
        return self._rule_plan(state)

    def _plan_with_llm(self, state: AgentState) -> AgentState:
        metadata = (
            self.tool_metadata_provider()
            if self.tool_metadata_provider is not None
            else DEFAULT_TOOL_METADATA
        )
        response = self.llm_client.complete(
            LLMRequest(
                messages=build_planner_messages(
                    query=state.get("query", ""),
                    role=state.get("role", "employee"),
                    tool_metadata=metadata,
                ),
                response_schema=PlannerDecision.model_json_schema(),
                temperature=0.0,
                max_tokens=512,
            )
        )
        llm_calls = list(state.get("llm_calls") or [])

        if response.status == "success" and response.parsed is not None:
            try:
                decision = PlannerDecision.model_validate(response.parsed)
                registered_tools = {str(item.get("name")) for item in metadata}
                unknown_tools = set(decision.selected_tools) - registered_tools
                if unknown_tools:
                    raise ValueError(f"unknown tools: {sorted(unknown_tools)}")
            except (ValueError, TypeError):
                llm_calls.append(
                    llm_call_summary(
                        response,
                        purpose="planner",
                        prompt_version=PLANNER_PROMPT_VERSION,
                        error_type="llm_invalid_output",
                    )
                )
            else:
                llm_calls.append(
                    llm_call_summary(
                        response,
                        purpose="planner",
                        prompt_version=PLANNER_PROMPT_VERSION,
                    )
                )
                return {
                    **state,
                    "task_type": decision.task_type,
                    "plan": decision.plan,
                    "selected_tools": decision.selected_tools,
                    "planner_reason": decision.reason,
                    "planner_source": "llm",
                    "llm_calls": llm_calls,
                    "llm_fallback_used": False,
                    "prompt_version": PLANNER_PROMPT_VERSION,
                }
        else:
            llm_calls.append(
                llm_call_summary(
                    response,
                    purpose="planner",
                    prompt_version=PLANNER_PROMPT_VERSION,
                )
            )

        return self._rule_plan(
            {
                **state,
                "llm_calls": llm_calls,
                "llm_fallback_used": True,
                "prompt_version": PLANNER_PROMPT_VERSION,
            }
        )

    def _rule_plan(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        task_type = self._classify(query)
        return {
            **state,
            "task_type": task_type,
            "plan": self.PLANS[task_type],
            "selected_tools": self.TOOLS[task_type],
            "planner_source": "rule",
        }

    def _classify(self, query: str) -> str:
        if any(word in query for word in ["统计", "数据", "多少", "列表"]):
            return "data_analysis"
        if any(word in query for word in ["审批", "申请", "采购", "流程"]):
            return "workflow_check"
        if any(word in query for word in ["分析", "风险", "项目"]):
            return "project_analysis"
        return "policy_qa"
