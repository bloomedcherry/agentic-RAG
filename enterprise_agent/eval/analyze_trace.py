"""Analyze runtime traces and write a Markdown summary."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from enterprise_agent.eval.common import dump_json, read_jsonl

DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[1] / "report" / "eval_summary.md"


def analyze_traces(
    trace_file: str | Path,
    report_path: str | Path = DEFAULT_REPORT_PATH,
) -> dict:
    traces = read_jsonl(trace_file)
    task_type_distribution = Counter(str(trace.get("task_type") or "unknown") for trace in traces)
    tool_call_distribution: Counter[str] = Counter()
    error_type_distribution = Counter(str(trace.get("error_type") or "none") for trace in traces)
    latency_by_task_type: dict[str, list[float]] = {}

    for trace in traces:
        task_type = str(trace.get("task_type") or "unknown")
        latency_by_task_type.setdefault(task_type, []).append(float(trace.get("latency") or 0.0))
        for call in trace.get("tool_calls") or []:
            tool_call_distribution[str(call.get("name") or "unknown")] += 1

    retry_candidates = [
        trace for trace in traces if _is_retry_action((trace.get("verifier_result") or {}).get("suggested_action"))
    ]
    retry_successes = [
        trace for trace in retry_candidates if bool((trace.get("verifier_result") or {}).get("pass"))
    ]
    metrics = {
        "total": len(traces),
        "task_type_distribution": dict(task_type_distribution),
        "tool_call_distribution": dict(tool_call_distribution),
        "error_type_distribution": dict(error_type_distribution),
        "retry_success_rate": _ratio(len(retry_successes), len(retry_candidates)),
        "latency_breakdown": {
            task_type: {
                "count": len(values),
                "avg": round(sum(values) / len(values), 6) if values else 0.0,
                "max": round(max(values), 6) if values else 0.0,
            }
            for task_type, values in sorted(latency_by_task_type.items())
        },
    }
    _write_markdown(metrics, report_path)
    return metrics


def _write_markdown(metrics: dict, report_path: str | Path) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M4 Eval Summary",
        "",
        f"- Total traces: {metrics['total']}",
        f"- Retry success rate: {metrics['retry_success_rate']}",
        "",
        "## Task Type Distribution",
        "",
    ]
    lines.extend(_counter_lines(metrics["task_type_distribution"]))
    lines.extend(["", "## Tool Call Distribution", ""])
    lines.extend(_counter_lines(metrics["tool_call_distribution"]))
    lines.extend(["", "## Error Type Distribution", ""])
    lines.extend(_counter_lines(metrics["error_type_distribution"]))
    lines.extend(["", "## Latency Breakdown", ""])
    for task_type, values in metrics["latency_breakdown"].items():
        lines.append(
            f"- {task_type}: count={values['count']}, avg={values['avg']}, max={values['max']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _counter_lines(counter: dict) -> list[str]:
    if not counter:
        return ["- none: 0"]
    return [f"- {key}: {value}" for key, value in sorted(counter.items())]


def _is_retry_action(action: object) -> bool:
    return bool(action) and str(action) != "none"


def _ratio(value: int, total: int) -> float:
    return value / total if total else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze runtime traces.")
    parser.add_argument("--trace-file", required=True)
    parser.add_argument("--report-file", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()
    print(dump_json(analyze_traces(args.trace_file, report_path=args.report_file)))


if __name__ == "__main__":
    main()
