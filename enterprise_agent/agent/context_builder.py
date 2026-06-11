"""Build a compact answer context from tool outputs."""

from __future__ import annotations

import json

from enterprise_agent.agent.state import AgentState

MAX_CONTEXT_CHARS = 1200
MAX_DOCUMENTS = 3
MAX_DOCUMENT_CHARS = 240


class ContextBuilder:
    def build(self, state: AgentState) -> AgentState:
        lines = [
            f"用户角色：{state.get('role', '')}",
            f"任务类型：{state.get('task_type', '')}",
            "回答约束：必须包含来源；证据不足时必须明确说明。",
        ]
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
        return {**state, "context": "\n".join(lines)[:MAX_CONTEXT_CHARS]}
