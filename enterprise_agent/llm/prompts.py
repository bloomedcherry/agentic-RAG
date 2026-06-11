"""Versioned prompts for LLM-backed agent components."""

from __future__ import annotations

import json

PLANNER_PROMPT_VERSION = "m5-planner-v1"
ANSWER_PROMPT_VERSION = "m5-answer-v1"


def build_planner_messages(
    *,
    query: str,
    role: str,
    tool_metadata: list[dict],
) -> list[dict[str, str]]:
    tools = [
        {
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "permission": item.get("permission", ""),
            "risk_level": item.get("risk_level", ""),
        }
        for item in tool_metadata
    ]
    return [
        {
            "role": "system",
            "content": (
                "You are an enterprise task planner. Return one JSON object matching "
                "the supplied schema. Select only listed tools. Plan the work but do "
                "not execute tools or claim that permission has been granted."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "query": query,
                    "user_role": role,
                    "available_tools": tools,
                },
                ensure_ascii=False,
            ),
        },
    ]


def build_answer_messages(
    *,
    query: str,
    task_type: str,
    context: str,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Answer only from the supplied evidence context. Never invent facts, "
                "tool results, approvals, or business data. State that evidence is "
                "insufficient when needed. Include source names for knowledge-based "
                "answers. Return the final answer only without internal reasoning or "
                "<think> blocks. Be concise. List at most 5 records or bullets and "
                "summarize any remaining items. For analysis tasks, return Markdown "
                "with a heading."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "query": query,
                    "task_type": task_type,
                    "evidence_context": context,
                },
                ensure_ascii=False,
            ),
        },
    ]
