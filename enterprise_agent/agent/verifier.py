"""Rule-based runtime result verifier."""

from __future__ import annotations

import re

from enterprise_agent.agent.retry import decide_next_action

RAG_TASKS = {"policy_qa", "workflow_check", "project_analysis"}
SOURCE_FILE_PATTERN = re.compile(
    r"[\w\u4e00-\u9fff./-]+\.(?:md|pdf|txt|docx?|xlsx?|csv|json)\b",
    flags=re.IGNORECASE,
)


def verify(state: dict) -> dict:
    issues: list[dict[str, str]] = []
    task_type = state.get("task_type")
    answer = state.get("answer") or ""
    tool_calls = state.get("tool_calls") or []
    retrieved_docs = state.get("retrieved_docs") or []

    _check_permission(tool_calls, issues)
    _check_retrieval(task_type, retrieved_docs, issues)
    _check_citation(task_type, retrieved_docs, answer, issues)
    _check_sql(tool_calls, issues)
    _check_report_format(task_type, tool_calls, answer, issues)

    result = {
        "pass": not issues,
        "issues": issues,
        "suggested_action": "none",
    }
    if issues:
        result["suggested_action"] = decide_next_action(result)
    return result


def _check_permission(tool_calls: list[dict], issues: list[dict[str, str]]) -> None:
    denied_tools = [call.get("name") for call in tool_calls if call.get("status") == "permission_denied"]
    if not denied_tools:
        return
    for tool_name in denied_tools:
        if any(call.get("name") == tool_name and call.get("status") == "success" for call in tool_calls):
            issues.append(
                {
                    "type": "permission_violation",
                    "message": f"{tool_name} 权限拒绝后仍被执行",
                }
            )
            return
    issues.append({"type": "permission_denied", "message": f"当前角色无权调用 {denied_tools[0]}"})


def _check_retrieval(task_type: str | None, retrieved_docs: list[dict], issues: list[dict[str, str]]) -> None:
    if task_type in RAG_TASKS and not retrieved_docs:
        issues.append({"type": "retrieval_empty", "message": "知识库检索结果为空"})


def _check_citation(
    task_type: str | None,
    retrieved_docs: list[dict],
    answer: str,
    issues: list[dict[str, str]],
) -> None:
    has_citation = (
        "来源" in answer
        or "source" in answer.lower()
        or "chunk_id" in answer
        or SOURCE_FILE_PATTERN.search(answer) is not None
    )
    if task_type in RAG_TASKS and retrieved_docs and not has_citation:
        issues.append({"type": "missing_citation", "message": "回答缺少引用来源"})


def _check_sql(tool_calls: list[dict], issues: list[dict[str, str]]) -> None:
    for call in tool_calls:
        if call.get("name") == "query_sql" and call.get("status") not in {"success", "permission_denied"}:
            issues.append({"type": "sql_error", "message": "SQL 工具执行失败"})
            return


def _check_report_format(
    task_type: str | None,
    tool_calls: list[dict],
    answer: str,
    issues: list[dict[str, str]],
) -> None:
    generated = any(call.get("name") == "generate_report" and call.get("status") == "success" for call in tool_calls)
    if task_type in {"project_analysis", "data_analysis"} and generated and not answer.lstrip().startswith("#"):
        issues.append({"type": "format_error", "message": "报告输出缺少 Markdown 标题"})
