import sqlite3

import pytest

from enterprise_agent.rag import build_index
from enterprise_agent.tools.base import BaseTool, ToolResult
from enterprise_agent.tools.registry import ToolRegistry
from enterprise_agent.tools.runtime_tools import (
    GenerateReportTool,
    QuerySqlTool,
    SearchKbTool,
    WorkflowCheckTool,
)


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo input text."
    input_schema = {"type": "object", "required": ["text"]}
    output_schema = {"type": "object", "required": ["text"]}

    def run(self, **kwargs):
        return ToolResult(status="success", output={"text": kwargs["text"]})


def test_tool_registry_registers_and_rejects_invalid_tools():
    registry = ToolRegistry()
    registry.register(EchoTool())

    assert registry.get("echo").name == "echo"
    assert registry.list_metadata()[0]["name"] == "echo"

    with pytest.raises(ValueError, match="duplicate"):
        registry.register(EchoTool())

    class EmptyNameTool(EchoTool):
        name = ""

    with pytest.raises(ValueError, match="name"):
        registry.register(EmptyNameTool())


def test_search_kb_tool_wraps_retriever(tmp_path):
    index_dir = tmp_path / "index"
    chunks = [
        {
            "chunk_id": "travel_chunk_001",
            "source": "travel.md",
            "doc_type": "policy",
            "title": "差旅报销制度",
            "content": "差旅报销需要提交发票、行程单、审批单和费用明细。",
            "metadata": {},
        }
    ]
    build_index.write_index(chunks, index_dir=index_dir)

    result = SearchKbTool(index_dir=index_dir).execute(query="差旅报销需要哪些材料", top_k=1)

    assert result.status == "success"
    assert result.output["documents"][0]["chunk_id"] == "travel_chunk_001"
    assert result.latency >= 0


def test_query_sql_tool_allows_only_controlled_query_types(tmp_path):
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

    result = QuerySqlTool(db_path=db_path).execute(query_type="project_risks", params={"project": "A"})

    assert result.status == "success"
    assert result.output["rows"][0]["name"] == "A 项目"
    assert result.output["rows"][0]["risk_level"] == "高"
    assert result.output["rows"][0]["source"] == "project_001.md"
    assert result.output["rows"][0]["risks"] == "供应商交付波动"

    denied = QuerySqlTool(db_path=db_path).execute(query_type="DROP TABLE projects", params={})

    assert denied.status == "error"
    assert "unsupported query_type" in denied.error


def test_workflow_check_tool_reads_rules(tmp_path):
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

    result = WorkflowCheckTool(rules_path=rules_path).execute(workflow_type="purchase", amount=8000)

    assert result.status == "success"
    assert result.output["approval_required"] is True
    assert result.output["approver"] == "部门经理"


def test_generate_report_tool_returns_markdown_with_sources():
    tool_outputs = {
        "search_kb": {
            "documents": [
                {
                    "source": "risk.md",
                    "content": "A 项目存在预算超支和交付延期风险。",
                    "score": 0.9,
                }
            ]
        }
    }

    result = GenerateReportTool().execute(
        query="帮我分析 A 项目当前有哪些风险。",
        task_type="project_analysis",
        tool_outputs=tool_outputs,
    )

    assert result.status == "success"
    assert result.output["markdown"].startswith("# 分析草稿")
    assert "risk.md" in result.output["markdown"]
