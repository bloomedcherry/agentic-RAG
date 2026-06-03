"""Concrete M2 tools used by the LangGraph runtime."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from enterprise_agent.rag import retriever
from enterprise_agent.tools.base import BaseTool, ToolResult

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PACKAGE_ROOT / "data" / "business.db"
DEFAULT_WORKFLOW_RULES_PATH = PACKAGE_ROOT / "data" / "workflow_rules.json"


class SearchKbTool(BaseTool):
    name = "search_kb"
    description = "Search the enterprise knowledge base."
    input_schema = {"type": "object", "required": ["query"]}
    output_schema = {"type": "object", "required": ["documents"]}
    permission = "read_knowledge_base"
    risk_level = "low"

    def __init__(self, index_dir: str | Path | None = None) -> None:
        self.index_dir = index_dir

    def run(self, **kwargs: Any) -> ToolResult:
        documents = retriever.retrieve(
            kwargs["query"],
            top_k=int(kwargs.get("top_k", 5)),
            filters=kwargs.get("filters"),
            index_dir=self.index_dir,
        )
        return ToolResult(status="success", output={"documents": documents})


class QuerySqlTool(BaseTool):
    name = "query_sql"
    description = "Run controlled business data queries."
    input_schema = {"type": "object", "required": ["query_type"]}
    output_schema = {"type": "object", "required": ["rows"]}
    permission = "read_business_data"
    risk_level = "medium"

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def run(self, **kwargs: Any) -> ToolResult:
        query_type = kwargs["query_type"]
        params = kwargs.get("params") or {}
        if query_type == "project_risks":
            project = params.get("project", "")
            sql = (
                "SELECT name, status, risk_level, owner, budget, source, milestone, risks "
                "FROM projects WHERE name LIKE ? ORDER BY name"
            )
            bindings = (f"%{project}%",)
        elif query_type == "high_risk_projects":
            sql = (
                "SELECT name, status, risk_level, owner, budget, source, milestone, risks "
                "FROM projects WHERE risk_level = '高' ORDER BY name"
            )
            bindings = ()
        else:
            return ToolResult(
                status="error",
                error=f"unsupported query_type: {query_type}",
                error_type="sql_error",
            )

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(sql, bindings).fetchall()]
        return ToolResult(status="success", output={"rows": rows, "query_type": query_type})


class WorkflowCheckTool(BaseTool):
    name = "workflow_check"
    description = "Evaluate controlled workflow approval rules."
    input_schema = {"type": "object", "required": ["workflow_type", "amount"]}
    output_schema = {"type": "object", "required": ["approval_required"]}
    permission = "read_workflow_rules"
    risk_level = "low"

    def __init__(self, rules_path: str | Path = DEFAULT_WORKFLOW_RULES_PATH) -> None:
        self.rules_path = Path(rules_path)

    def run(self, **kwargs: Any) -> ToolResult:
        workflow_type = kwargs.get("workflow_type", "purchase")
        amount = float(kwargs.get("amount") or 0)
        rules = json.loads(self.rules_path.read_text(encoding="utf-8"))
        for rule in rules.get(workflow_type, []):
            min_amount = rule.get("min_amount", float("-inf"))
            max_amount = rule.get("max_amount", float("inf"))
            if amount >= min_amount and amount < max_amount:
                output = dict(rule)
                output["workflow_type"] = workflow_type
                output["amount"] = amount
                return ToolResult(status="success", output=output)
        return ToolResult(
            status="error",
            error=f"no matching workflow rule for {workflow_type} amount={amount}",
            error_type="workflow_error",
        )


class GenerateReportTool(BaseTool):
    name = "generate_report"
    description = "Generate a template markdown analysis draft from tool outputs."
    input_schema = {"type": "object", "required": ["query", "task_type", "tool_outputs"]}
    output_schema = {"type": "object", "required": ["markdown"]}
    permission = "generate_draft"
    risk_level = "low"

    def run(self, **kwargs: Any) -> ToolResult:
        query = kwargs["query"]
        task_type = kwargs["task_type"]
        tool_outputs = kwargs.get("tool_outputs") or {}
        lines = ["# 分析草稿", "", f"- 任务类型：{task_type}", f"- 用户问题：{query}", ""]

        documents = (tool_outputs.get("search_kb") or {}).get("documents") or []
        rows = (tool_outputs.get("query_sql") or {}).get("rows") or []
        if documents:
            lines.append("## 知识库证据")
            for doc in documents[:5]:
                lines.append(f"- 来源：{doc.get('source')}；摘要：{doc.get('content', '')[:120]}")
            lines.append("")
        if rows:
            lines.append("## 业务数据")
            for row in rows[:5]:
                lines.append(
                    "- "
                    + "，".join(f"{key}：{value}" for key, value in row.items())
                )
            lines.append("")
        if not documents and not rows:
            lines.append("证据不足：未检索到可用知识库证据或业务数据。")
        else:
            lines.append("## 初步结论")
            lines.append("- 以上内容为模板草稿，需要业务负责人复核后再对外发布。")
        return ToolResult(status="success", output={"markdown": "\n".join(lines)})


def extract_amount(text: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*元", text)
    return float(match.group(1)) if match else 0.0


def extract_project_keyword(text: str) -> str:
    match = re.search(r"([A-Za-z0-9\u4e00-\u9fff]+)\s*项目", text)
    return f"{match.group(1)} 项目" if match else ""
