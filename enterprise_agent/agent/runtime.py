"""Public runtime wrapper for M2 LangGraph execution."""

from __future__ import annotations

import time
from pathlib import Path

from enterprise_agent.agent.graph import build_graph
from enterprise_agent.tools.registry import ToolRegistry
from enterprise_agent.tools.runtime_tools import (
    DEFAULT_DB_PATH,
    DEFAULT_WORKFLOW_RULES_PATH,
    GenerateReportTool,
    QuerySqlTool,
    SearchKbTool,
    WorkflowCheckTool,
)


class Runtime:
    def __init__(
        self,
        index_dir: str | Path | None = None,
        db_path: str | Path = DEFAULT_DB_PATH,
        workflow_rules_path: str | Path = DEFAULT_WORKFLOW_RULES_PATH,
    ) -> None:
        self.registry = ToolRegistry()
        self.registry.register(SearchKbTool(index_dir=index_dir))
        self.registry.register(QuerySqlTool(db_path=db_path))
        self.registry.register(WorkflowCheckTool(rules_path=workflow_rules_path))
        self.registry.register(GenerateReportTool())
        self.graph = build_graph(self.registry)

    def run(self, query: str, user_role: str = "employee") -> dict:
        start = time.perf_counter()
        result = self.graph.invoke(
            {
                "query": query,
                "role": user_role,
                "tool_calls": [],
                "tool_outputs": {},
                "retrieved_docs": [],
                "errors": [],
            }
        )
        result["latency"] = time.perf_counter() - start
        return result
