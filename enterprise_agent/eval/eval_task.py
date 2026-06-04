"""Evaluate end-to-end task success from runtime traces."""

from __future__ import annotations

import argparse
from pathlib import Path

from enterprise_agent.eval.common import dump_json, indexed_by_id, latest_traces_for_tasks, read_jsonl


def evaluate_tasks(trace_file: str | Path, eval_file: str | Path) -> dict:
    tasks = indexed_by_id(read_jsonl(eval_file))
    traces = latest_traces_for_tasks(read_jsonl(trace_file), set(tasks))
    total = 0
    successful = 0
    citation_total = 0
    citation_ok = 0
    verifier_ok = 0
    latency_sum = 0.0
    failed_cases = []

    for trace in traces:
        task_id = str(trace.get("task_id"))
        task = tasks.get(task_id)
        if not task:
            continue
        total += 1
        latency_sum += float(trace.get("latency") or 0.0)
        verifier_passed = bool((trace.get("verifier_result") or {}).get("pass"))
        if verifier_passed:
            verifier_ok += 1

        reasons = _failure_reasons(task, trace, verifier_passed)
        if task.get("need_citation"):
            citation_total += 1
            if "missing_citation" not in reasons:
                citation_ok += 1

        if not reasons:
            successful += 1
        else:
            failed_cases.append(
                {
                    "id": task_id,
                    "query": task.get("query", ""),
                    "reasons": reasons,
                }
            )

    return {
        "total": total,
        "task_success_rate": _ratio(successful, total),
        "citation_accuracy": _ratio(citation_ok, citation_total),
        "verifier_pass_rate": _ratio(verifier_ok, total),
        "average_latency": _round(_ratio(latency_sum, total)),
        "failed_cases": failed_cases,
    }


def _failure_reasons(task: dict, trace: dict, verifier_passed: bool) -> list[str]:
    reasons = []
    if trace.get("task_type") != task.get("expected_task_type"):
        reasons.append("wrong_task_type")
    actual_tools = {str(call.get("name")) for call in trace.get("tool_calls") or []}
    expected_tools = {str(tool) for tool in task.get("expected_tools") or []}
    if not expected_tools.issubset(actual_tools):
        reasons.append("missing_tool")
    if not str(trace.get("answer") or "").strip():
        reasons.append("empty_answer")
    if task.get("need_citation") and not _answer_has_citation(trace):
        reasons.append("missing_citation")
    if not verifier_passed:
        reasons.append("verifier_failed")
    return reasons


def _answer_has_citation(trace: dict) -> bool:
    answer = str(trace.get("answer") or "")
    for doc in trace.get("retrieved_docs") or []:
        source = str(doc.get("source") or "")
        chunk_id = str(doc.get("chunk_id") or "")
        if (source and source in answer) or (chunk_id and chunk_id in answer):
            return True
    return False


def _ratio(value: float, total: int) -> float:
    return value / total if total else 0.0


def _round(value: float) -> float:
    return round(value, 6)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate end-to-end task success from traces.")
    parser.add_argument("--trace-file", required=True)
    parser.add_argument("--eval-file", required=True)
    args = parser.parse_args()
    print(dump_json(evaluate_tasks(args.trace_file, args.eval_file)))


if __name__ == "__main__":
    main()
