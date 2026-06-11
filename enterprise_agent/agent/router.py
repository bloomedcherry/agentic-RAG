"""Map planned task types to the fixed M2 tool sequence."""

from __future__ import annotations

from enterprise_agent.agent.state import AgentState


class Router:
    ROUTES = {
        "policy_qa": ["search_kb"],
        "workflow_check": ["search_kb", "workflow_check"],
        "project_analysis": ["search_kb", "generate_report"],
        "data_analysis": ["query_sql", "generate_report"],
    }

    def route(self, state: AgentState) -> AgentState:
        if state.get("planner_source") == "llm" and state.get("selected_tools"):
            return state
        return {**state, "selected_tools": self.ROUTES.get(state.get("task_type"), ["search_kb"])}
