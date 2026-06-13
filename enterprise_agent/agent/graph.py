"""LangGraph orchestration for the M2 runtime."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from enterprise_agent.agent.answer_generator import AnswerGenerator
from enterprise_agent.agent.context_builder import ContextBuilder
from enterprise_agent.agent.permission import check_permission
from enterprise_agent.agent.planner import Planner
from enterprise_agent.agent.router import Router
from enterprise_agent.agent.state import AgentState
from enterprise_agent.llm.base import BaseLLMClient
from enterprise_agent.memory.manager import MemoryManager
from enterprise_agent.tools.registry import ToolRegistry
from enterprise_agent.tools.runtime_tools import extract_amount, extract_project_keyword


def build_graph(
    registry: ToolRegistry,
    *,
    planner_llm_client: BaseLLMClient | None = None,
    answer_llm_client: BaseLLMClient | None = None,
    memory_manager: MemoryManager | None = None,
    checkpointer=None,
    answer_max_tokens: int = 1024,
    max_context_chars: int = 8000,
):
    planner = Planner(
        llm_client=planner_llm_client,
        tool_metadata_provider=registry.list_metadata,
    )
    router = Router()
    context_builder = ContextBuilder(max_context_chars=max_context_chars)
    answer_generator = AnswerGenerator(
        answer_llm_client,
        max_tokens=answer_max_tokens,
    )

    def memory_reader_node(state: AgentState) -> AgentState:
        if memory_manager is None:
            return state
        try:
            context = memory_manager.load_context(
                state.get("user_id", ""),
                state.get("thread_id", ""),
            )
        except Exception as exc:
            errors = list(state.get("errors") or [])
            errors.append({"type": "memory_read_error", "message": str(exc)})
            return {**state, "errors": errors}
        return {**state, "memory_context": _serializable_memory_context(context)}

    def planner_node(state: AgentState) -> AgentState:
        return planner.plan(state)

    def router_node(state: AgentState) -> AgentState:
        return router.route(state)

    def tool_executor_node(state: AgentState) -> AgentState:
        tool_outputs = dict(state.get("tool_outputs") or {})
        tool_calls = list(state.get("tool_calls") or [])
        retrieved_docs = list(state.get("retrieved_docs") or [])
        errors = list(state.get("errors") or [])

        for tool_name in state.get("selected_tools", []):
            tool = registry.get(tool_name)
            permission = check_permission(state.get("role", "employee"), tool)
            if not permission["allowed"]:
                tool_calls.append({"name": tool_name, "status": permission["error_type"]})
                errors.append({"type": permission["error_type"], "message": permission["message"]})
                break
            result = tool.execute(**_tool_args(tool_name, state, tool_outputs))
            tool_call = {"name": tool_name, "status": result.status}
            if result.error_type:
                tool_call["error_type"] = result.error_type
            tool_calls.append(tool_call)
            if result.status == "success":
                output = result.output or {}
                tool_outputs[tool_name] = output
                if tool_name == "search_kb":
                    retrieved_docs = output.get("documents") or []
            else:
                errors.append(
                    {
                        "type": result.error_type or "tool_error",
                        "message": result.error or f"{tool_name} failed",
                    }
                )

        return {
            **state,
            "tool_outputs": tool_outputs,
            "tool_calls": tool_calls,
            "retrieved_docs": retrieved_docs,
            "errors": errors,
        }

    def context_builder_node(state: AgentState) -> AgentState:
        return context_builder.build(state)

    def answer_generator_node(state: AgentState) -> AgentState:
        answer, metadata = answer_generator.generate(state)
        return {**state, "answer": answer, **metadata}

    def memory_writer_node(state: AgentState) -> AgentState:
        if memory_manager is None:
            return state
        try:
            memory_manager.append_exchange(
                state.get("user_id", ""),
                state.get("thread_id", ""),
                state.get("query", ""),
                state.get("answer", ""),
            )
        except Exception as exc:
            errors = list(state.get("errors") or [])
            errors.append({"type": "memory_write_error", "message": str(exc)})
            return {**state, "errors": errors}
        return state

    graph = StateGraph(AgentState)
    graph.add_node("memory_reader_node", memory_reader_node)
    graph.add_node("planner_node", planner_node)
    graph.add_node("router_node", router_node)
    graph.add_node("tool_executor_node", tool_executor_node)
    graph.add_node("context_builder_node", context_builder_node)
    graph.add_node("answer_generator_node", answer_generator_node)
    graph.add_node("memory_writer_node", memory_writer_node)
    graph.add_edge(START, "memory_reader_node")
    graph.add_edge("memory_reader_node", "planner_node")
    graph.add_edge("planner_node", "router_node")
    graph.add_edge("router_node", "tool_executor_node")
    graph.add_edge("tool_executor_node", "context_builder_node")
    graph.add_edge("context_builder_node", "answer_generator_node")
    graph.add_edge("answer_generator_node", "memory_writer_node")
    graph.add_edge("memory_writer_node", END)
    return graph.compile(checkpointer=checkpointer)


def _serializable_memory_context(context: dict) -> dict:
    result = dict(context)
    result["recent_messages"] = [
        {
            "seq": message.seq,
            "role": message.role,
            "content": message.content,
            "token_count": message.token_count,
            "estimated": message.estimated,
        }
        for message in context.get("recent_messages") or []
    ]
    return result


def _tool_args(tool_name: str, state: AgentState, tool_outputs: dict) -> dict:
    query = state.get("query", "")
    if tool_name == "search_kb":
        return {"query": query, "top_k": 5}
    if tool_name == "workflow_check":
        return {"workflow_type": "purchase", "amount": extract_amount(query)}
    if tool_name == "query_sql":
        if "高风险" in query:
            return {"query_type": "high_risk_projects", "params": {}}
        project = extract_project_keyword(query)
        query_type = "project_risks" if project else "high_risk_projects"
        return {"query_type": query_type, "params": {"project": project}}
    if tool_name == "generate_report":
        return {
            "query": query,
            "task_type": state.get("task_type", ""),
            "tool_outputs": tool_outputs,
        }
    return {}
