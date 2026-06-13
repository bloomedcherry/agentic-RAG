"""Build a compact answer context from tool outputs."""

from __future__ import annotations

import json

from enterprise_agent.agent.state import AgentState

MAX_CONTEXT_CHARS = 1200
MAX_DOCUMENTS = 3
MAX_DOCUMENT_CHARS = 240
MAX_RECENT_MESSAGES = 10
MAX_MEMORY_MESSAGE_CHARS = 2000


class ContextBuilder:
    def __init__(self, *, max_context_chars: int = MAX_CONTEXT_CHARS) -> None:
        self.max_context_chars = max_context_chars

    def build(self, state: AgentState) -> AgentState:
        lines = [
            f"用户角色：{state.get('role', '')}",
            f"任务类型：{state.get('task_type', '')}",
            "回答约束：必须包含来源；证据不足时必须明确说明。",
        ]
        memory_lines = _memory_lines(state.get("memory_context") or {})
        if memory_lines:
            lines.append("会话记忆：")
            lines.extend(memory_lines)
        documents = state.get("retrieved_docs") or []
        if documents:
            lines.append("知识库证据：")
            for doc in documents[:MAX_DOCUMENTS]:
                content = " ".join(str(doc.get("content", "")).split())
                lines.append(
                    f"- {doc.get('source')}: {content[:MAX_DOCUMENT_CHARS]}"
                )
        tool_outputs = state.get("tool_outputs") or {}
        for name, output in tool_outputs.items():
            if name in {"search_kb", "generate_report"}:
                continue
            serialized = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
            lines.append(f"工具结果 {name}: {serialized}")
        return {**state, "context": "\n".join(lines)[: self.max_context_chars]}


def _memory_lines(memory_context: dict) -> list[str]:
    lines: list[str] = []
    summary = memory_context.get("summary")
    if summary:
        serialized = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"- 历史摘要：{serialized[:240]}")
    recent_messages = memory_context.get("recent_messages") or []
    for message in recent_messages[-MAX_RECENT_MESSAGES:]:
        if isinstance(message, dict):
            role = message.get("role", "")
            content = message.get("content", "")
        else:
            role = getattr(message, "role", "")
            content = getattr(message, "content", "")
        compact = " ".join(str(content).split())
        lines.append(f"- {role}: {compact[:MAX_MEMORY_MESSAGE_CHARS]}")
    return lines
