from enterprise_agent.agent.planner import Planner
from enterprise_agent.agent.router import Router


def test_planner_classifies_policy_question():
    state = {"query": "差旅报销需要哪些材料？", "role": "employee"}

    planned = Planner().plan(state)

    assert planned["task_type"] == "policy_qa"
    assert "检索知识库" in planned["plan"][0]


def test_planner_classifies_workflow_and_analysis_tasks():
    planner = Planner()

    workflow = planner.plan({"query": "这个 8000 元采购申请是否需要审批？", "role": "employee"})
    project = planner.plan({"query": "帮我分析 A 项目当前有哪些风险。", "role": "manager"})
    data = planner.plan({"query": "统计当前高风险项目", "role": "manager"})

    assert workflow["task_type"] == "workflow_check"
    assert project["task_type"] == "project_analysis"
    assert data["task_type"] == "data_analysis"


def test_router_selects_tools_by_task_type():
    router = Router()

    assert router.route({"task_type": "policy_qa"})["selected_tools"] == ["search_kb"]
    assert router.route({"task_type": "workflow_check"})["selected_tools"] == [
        "search_kb",
        "workflow_check",
    ]
    assert router.route({"task_type": "project_analysis"})["selected_tools"] == [
        "search_kb",
        "generate_report",
    ]
    assert router.route({"task_type": "data_analysis"})["selected_tools"] == [
        "query_sql",
        "generate_report",
    ]
