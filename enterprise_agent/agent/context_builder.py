"""Build a compact answer context from tool outputs."""

from __future__ import annotations

from enterprise_agent.agent.state import AgentState


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
            for doc in documents[:5]:
                lines.append(f"- {doc.get('source')}: {doc.get('content')}")
        tool_outputs = state.get("tool_outputs") or {}
        for name, output in tool_outputs.items():
            if name != "search_kb":
                lines.append(f"工具结果 {name}: {output}")
        return {**state, "context": "\n".join(lines)}
