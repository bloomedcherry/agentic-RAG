"""Rule-based planner for M2 task classification."""

from __future__ import annotations

from enterprise_agent.agent.state import AgentState


class Planner:
    def plan(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        task_type = self._classify(query)
        plans = {
            "policy_qa": ["检索知识库", "基于来源生成制度问答"],
            "workflow_check": ["检索知识库", "读取流程规则", "判断是否需要审批"],
            "project_analysis": ["检索知识库", "生成项目分析草稿"],
            "data_analysis": ["查询业务数据", "生成数据分析草稿"],
        }
        return {**state, "task_type": task_type, "plan": plans[task_type]}

    def _classify(self, query: str) -> str:
        if any(word in query for word in ["统计", "数据", "多少", "列表"]):
            return "data_analysis"
        if any(word in query for word in ["审批", "申请", "采购", "流程"]):
            return "workflow_check"
        if any(word in query for word in ["分析", "风险", "项目"]):
            return "project_analysis"
        return "policy_qa"
