import sqlite3
import subprocess
import sys

from enterprise_agent.agent.runtime import Runtime
from enterprise_agent.rag import build_index


def _prepare_runtime_data(tmp_path):
    index_dir = tmp_path / "index"
    chunks = [
        {
            "chunk_id": "travel_chunk_001",
            "source": "travel.md",
            "doc_type": "policy",
            "title": "差旅报销制度",
            "content": "差旅报销需要提交发票、行程单、审批单和费用明细。",
            "metadata": {},
        },
        {
            "chunk_id": "purchase_chunk_001",
            "source": "purchase.md",
            "doc_type": "workflow",
            "title": "采购审批流程",
            "content": "采购金额达到 5000 元需要部门经理审批。",
            "metadata": {},
        },
        {
            "chunk_id": "project_a_chunk_001",
            "source": "project_a.md",
            "doc_type": "report",
            "title": "A 项目风险",
            "content": "A 项目当前存在预算超支、供应商延期和验收范围不清风险。",
            "metadata": {},
        },
    ]
    build_index.write_index(chunks, index_dir=index_dir)

    rules_path = tmp_path / "workflow_rules.json"
    rules_path.write_text(
        """
        {
          "purchase": [
            {"max_amount": 5000, "approval_required": false, "approver": null},
            {"min_amount": 5000, "approval_required": true, "approver": "部门经理"}
          ]
        }
        """,
        encoding="utf-8",
    )

    db_path = tmp_path / "business.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE projects (
                name TEXT, status TEXT, risk_level TEXT, owner TEXT, budget REAL,
                source TEXT, department TEXT, milestone TEXT, risks TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO projects VALUES (
                'A 项目', '进行中', '高', '张三', 120000,
                'project_001.md', '采购部', '接口联调', '供应商交付波动'
            )
            """
        )

    return index_dir, db_path, rules_path


def test_runtime_runs_policy_question_through_langgraph(tmp_path):
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        llm_enabled=False,
    ).run(
        "差旅报销需要哪些材料？",
        user_role="employee",
    )

    assert result["task_type"] == "policy_qa"
    assert result["tool_calls"] == [{"name": "search_kb", "status": "success"}]
    assert "发票" in result["answer"]
    assert "来源" in result["answer"]
    assert "结论：" in result["answer"]
    assert "## 操作记录样例" not in result["answer"]


def test_runtime_routes_workflow_and_project_analysis(tmp_path):
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    runtime = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        llm_enabled=False,
    )

    workflow = runtime.run("这个 8000 元采购申请是否需要审批？", user_role="employee")
    project = runtime.run("帮我分析 A 项目当前有哪些风险。", user_role="manager")

    assert workflow["task_type"] == "workflow_check"
    assert [call["name"] for call in workflow["tool_calls"]] == ["search_kb", "workflow_check"]
    assert "需要审批" in workflow["answer"]

    assert project["task_type"] == "project_analysis"
    assert [call["name"] for call in project["tool_calls"]] == ["search_kb", "generate_report"]
    assert "# 分析草稿" in project["answer"]


def test_runtime_routes_data_analysis_through_sql_and_report(tmp_path):
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        llm_enabled=False,
    ).run(
        "统计当前高风险项目",
        user_role="manager",
    )

    assert result["task_type"] == "data_analysis"
    assert [call["name"] for call in result["tool_calls"]] == ["query_sql", "generate_report"]
    assert "A 项目" in result["answer"]
    assert "risk_level：高" in result["answer"]


def test_cli_runs_from_project_root(tmp_path):
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_agent.app",
            "--query",
            "差旅报销需要哪些材料？",
            "--role",
            "employee",
            "--index-dir",
            str(index_dir),
            "--db-path",
            str(db_path),
            "--workflow-rules-path",
            str(rules_path),
            "--no-llm",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "task_type: policy_qa" in completed.stdout
    assert "tool_calls:" in completed.stdout
    assert "search_kb" in completed.stdout
