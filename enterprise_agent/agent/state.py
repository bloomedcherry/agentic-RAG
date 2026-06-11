"""Shared state shape for the M2 LangGraph runtime."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    task_id: str
    query: str
    role: str
    task_type: str
    plan: list[str]
    selected_tools: list[str]
    tool_calls: list[dict[str, Any]]
    retrieved_docs: list[dict[str, Any]]
    tool_outputs: dict[str, dict[str, Any]]
    context: str
    answer: str
    errors: list[Any]
    verifier_result: dict[str, Any]
    verifier_history: list[dict[str, Any]]
    llm_calls: list[dict[str, Any]]
    llm_fallback_used: bool
    prompt_version: str
    planner_source: str
    planner_reason: str
    trace_path: str
    latency: float
