"""Evaluate tool selection, tool success, and permission blocking."""

from __future__ import annotations

import argparse
from pathlib import Path

from enterprise_agent.eval.common import dump_json, indexed_by_id, latest_traces_for_tasks, read_jsonl


def evaluate_tools(trace_file: str | Path, eval_file: str | Path) -> dict:
    tasks = indexed_by_id(read_jsonl(eval_file))
    traces = latest_traces_for_tasks(read_jsonl(trace_file), set(tasks))
    total = 0
    correct_tool_calls = 0
    expected_tool_slots = 0
    successful_expected_tools = 0
    permission_expected = 0
    permission_correct = 0
    wrong_tool_cases = []

    for trace in traces:
        task_id = str(trace.get("task_id"))
        task = tasks.get(task_id)
        if not task:
            continue
        total += 1
        expected_tools = [str(tool) for tool in task.get("expected_tools") or []]
        actual_calls = trace.get("tool_calls") or []
        actual_tools = [str(call.get("name")) for call in actual_calls]
        actual_status_by_tool = {str(call.get("name")): call.get("status") for call in actual_calls}

        if set(expected_tools).issubset(set(actual_tools)):
            correct_tool_calls += 1
        else:
            wrong_tool_cases.append(
                {
                    "id": task_id,
                    "expected_tools": expected_tools,
                    "actual_tools": actual_tools,
                }
            )

        expected_tool_slots += len(expected_tools)
        successful_expected_tools += sum(
            1 for tool in expected_tools if actual_status_by_tool.get(tool) == "success"
        )

        if _expects_permission_denied(task):
            permission_expected += 1
            if trace.get("error_type") == "permission_denied":
                permission_correct += 1

    return {
        "total": total,
        "tool_call_accuracy": _ratio(correct_tool_calls, total),
        "tool_success_rate": _ratio(successful_expected_tools, expected_tool_slots),
        "permission_blocking_accuracy": _ratio(permission_correct, permission_expected),
        "wrong_tool_cases": wrong_tool_cases,
    }


def _expects_permission_denied(task: dict) -> bool:
    if task.get("expected_error_type") == "permission_denied":
        return True
    return bool(task.get("need_sql")) and task.get("user_role") == "employee"


def _ratio(value: int, total: int) -> float:
    return value / total if total else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate runtime tool calls from traces.")
    parser.add_argument("--trace-file", required=True)
    parser.add_argument("--eval-file", required=True)
    args = parser.parse_args()
    print(dump_json(evaluate_tools(args.trace_file, args.eval_file)))


if __name__ == "__main__":
    main()
