"""LangGraph orchestration for the M2 runtime."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from enterprise_agent.agent.context_builder import ContextBuilder
from enterprise_agent.agent.planner import Planner
from enterprise_agent.agent.router import Router
from enterprise_agent.agent.state import AgentState
from enterprise_agent.tools.registry import ToolRegistry
from enterprise_agent.tools.runtime_tools import extract_amount, extract_project_keyword


def build_graph(registry: ToolRegistry):
    planner = Planner()
    router = Router()
    context_builder = ContextBuilder()

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
            result = tool.execute(**_tool_args(tool_name, state, tool_outputs))
            tool_calls.append({"name": tool_name, "status": result.status})
            if result.status == "success":
                output = result.output or {}
                tool_outputs[tool_name] = output
                if tool_name == "search_kb":
                    retrieved_docs = output.get("documents") or []
            else:
                errors.append(result.error or f"{tool_name} failed")

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
        return {**state, "answer": _generate_answer(state)}

    graph = StateGraph(AgentState)
    graph.add_node("planner_node", planner_node)
    graph.add_node("router_node", router_node)
    graph.add_node("tool_executor_node", tool_executor_node)
    graph.add_node("context_builder_node", context_builder_node)
    graph.add_node("answer_generator_node", answer_generator_node)
    graph.add_edge(START, "planner_node")
    graph.add_edge("planner_node", "router_node")
    graph.add_edge("router_node", "tool_executor_node")
    graph.add_edge("tool_executor_node", "context_builder_node")
    graph.add_edge("context_builder_node", "answer_generator_node")
    graph.add_edge("answer_generator_node", END)
    return graph.compile()


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


def _generate_answer(state: AgentState) -> str:
    outputs = state.get("tool_outputs") or {}
    if state.get("task_type") in {"project_analysis", "data_analysis"}:
        report = outputs.get("generate_report", {}).get("markdown")
        return report or "证据不足：未生成分析草稿。"

    if state.get("task_type") == "workflow_check":
        workflow = outputs.get("workflow_check") or {}
        documents = outputs.get("search_kb", {}).get("documents") or []
        source_line = _source_line(documents)
        if workflow.get("approval_required") is True:
            return f"需要审批，审批人：{workflow.get('approver') or '未配置'}。\n{source_line}"
        if workflow.get("approval_required") is False:
            return f"不需要审批。\n{source_line}"
        return f"证据不足：无法匹配流程规则。\n{source_line}"

    documents = outputs.get("search_kb", {}).get("documents") or []
    if not documents:
        return "证据不足：知识库未检索到可用来源。"
    return _generate_policy_answer(state.get("query", ""), documents)


def _source_line(documents: list[dict]) -> str:
    if not documents:
        return "来源：知识库未命中。"
    sources = "，".join(dict.fromkeys(str(doc.get("source")) for doc in documents[:5]))
    return f"来源：{sources}"


def _generate_policy_answer(query: str, documents: list[dict]) -> str:
    evidence_text = "\n".join(str(doc.get("content", "")) for doc in documents[:5])
    if "差旅报销" in query:
        materials = [
            item
            for item in ["行程单", "发票", "审批单", "费用明细", "付款账户", "例外材料"]
            if item in evidence_text
        ]
        if materials:
            return (
                "结论：差旅报销通常需要提交以下材料：\n"
                + "\n".join(f"- {item}" for item in materials)
                + f"\n{_source_line(documents)}"
            )

    summaries = []
    for doc in documents[:3]:
        first_section = str(doc.get("content", "")).split("##", maxsplit=1)[0]
        cleaned = " ".join(first_section.split())
        if cleaned:
            summaries.append(f"- {cleaned[:120]}")
    if not summaries:
        return f"证据不足：知识库命中来源但内容不可用于回答。\n{_source_line(documents)}"
    return "结论：根据知识库检索结果，相关要求如下：\n" + "\n".join(summaries) + f"\n{_source_line(documents)}"
