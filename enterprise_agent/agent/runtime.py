"""Public runtime wrapper for LangGraph execution."""

from __future__ import annotations

import time
from pathlib import Path

from enterprise_agent.agent.graph import build_graph
from enterprise_agent.agent.retry import decide_next_action
from enterprise_agent.agent.trace import DEFAULT_TRACE_PATH, write_trace
from enterprise_agent.agent.verifier import verify
from enterprise_agent.config import Settings
from enterprise_agent.llm.base import BaseLLMClient
from enterprise_agent.llm.client import OpenAICompatibleClient
from enterprise_agent.tools.registry import ToolRegistry
from enterprise_agent.tools.runtime_tools import (
    DEFAULT_DB_PATH,
    DEFAULT_WORKFLOW_RULES_PATH,
    GenerateReportTool,
    QuerySqlTool,
    SearchKbTool,
    WorkflowCheckTool,
)


class Runtime:
    def __init__(
        self,
        index_dir: str | Path | None = None,
        db_path: str | Path = DEFAULT_DB_PATH,
        workflow_rules_path: str | Path = DEFAULT_WORKFLOW_RULES_PATH,
        trace_path: str | Path = DEFAULT_TRACE_PATH,
        planner_llm_client: BaseLLMClient | None = None,
        answer_llm_client: BaseLLMClient | None = None,
        settings: Settings | None = None,
        llm_enabled: bool | None = None,
    ) -> None:
        self.settings = settings or Settings()
        configured_enabled = (
            self.settings.llm_enabled if llm_enabled is None else llm_enabled
        )
        if planner_llm_client is None and configured_enabled:
            planner_llm_client = _build_utility_client(self.settings)
        if answer_llm_client is None and configured_enabled:
            answer_llm_client = _build_main_client(self.settings)
        self.planner_llm_client = planner_llm_client
        self.answer_llm_client = answer_llm_client

        self.registry = ToolRegistry()
        self.registry.register(SearchKbTool(index_dir=index_dir))
        self.registry.register(QuerySqlTool(db_path=db_path))
        self.registry.register(WorkflowCheckTool(rules_path=workflow_rules_path))
        self.registry.register(GenerateReportTool())
        self.graph = build_graph(
            self.registry,
            planner_llm_client=self.planner_llm_client,
            answer_llm_client=self.answer_llm_client,
        )
        self.trace_path = Path(trace_path)

    def run(self, query: str, user_role: str = "employee", task_id: str | None = None) -> dict:
        start = time.perf_counter()
        initial_state = {
            "query": query,
            "role": user_role,
            "tool_calls": [],
            "tool_outputs": {},
            "retrieved_docs": [],
            "errors": [],
        }
        if task_id:
            initial_state["task_id"] = task_id
        result = self.graph.invoke(initial_state)
        result["latency"] = time.perf_counter() - start
        verifier_result = verify(result)
        result["verifier_result"] = verifier_result
        result["verifier_history"] = [verifier_result]
        if not verifier_result["pass"]:
            action = decide_next_action(verifier_result)
            result["answer"] = _apply_fallback(result, action)
            result["verifier_result"] = verify(result)
            result["verifier_history"].append(result["verifier_result"])
            if not result["verifier_result"]["pass"]:
                result["verifier_result"]["suggested_action"] = action
        write_trace(result, path=self.trace_path)
        return result


def _apply_fallback(state: dict, action: str) -> str:
    if action == "retry_with_citation":
        return _with_citation(state)
    if action == "fallback_insufficient_evidence":
        return "证据不足：知识库未检索到可用来源，无法给出可靠结论。"
    if action == "fallback_without_data_claim":
        return "证据不足：业务数据查询失败，不能生成数据结论。"
    if action == "refusal":
        message = _first_error_message(state) or "当前角色无权执行该操作。"
        return f"拒绝执行：{message}"
    if action == "retry_with_format":
        answer = state.get("answer") or ""
        return answer if answer.lstrip().startswith("#") else f"# 分析草稿\n\n{answer}"
    return state.get("answer", "")


def _with_citation(state: dict) -> str:
    answer = state.get("answer") or ""
    docs = state.get("retrieved_docs") or []
    if not docs:
        return answer
    sources = "，".join(dict.fromkeys(str(doc.get("source") or doc.get("chunk_id")) for doc in docs[:5]))
    return f"{answer}\n来源：{sources}"


def _first_error_message(state: dict) -> str:
    for error in state.get("errors") or []:
        if isinstance(error, dict) and error.get("message"):
            return error["message"]
        if isinstance(error, str):
            return error
    return ""


def _build_main_client(settings: Settings) -> BaseLLMClient | None:
    if not settings.main_llm_base_url or not settings.main_llm_model:
        return None
    return OpenAICompatibleClient(
        base_url=settings.main_llm_base_url,
        api_key=settings.main_llm_api_key or "local",
        model=settings.main_llm_model,
        timeout=settings.main_llm_timeout,
        max_attempts=settings.llm_max_attempts,
        fallback_base_url=settings.main_llm_fallback_base_url,
        fallback_api_key=settings.main_llm_fallback_api_key,
        fallback_model=settings.main_llm_fallback_model,
    )


def _build_utility_client(settings: Settings) -> BaseLLMClient | None:
    if not settings.utility_llm_base_url or not settings.utility_llm_model:
        return None
    return OpenAICompatibleClient(
        base_url=settings.utility_llm_base_url,
        api_key=settings.utility_llm_api_key or "local",
        model=settings.utility_llm_model,
        timeout=settings.utility_llm_timeout,
        max_attempts=settings.llm_max_attempts,
    )
