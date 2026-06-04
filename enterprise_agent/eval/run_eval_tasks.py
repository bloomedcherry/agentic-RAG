"""Run eval tasks through the Runtime to produce traces."""

from __future__ import annotations

import argparse
from pathlib import Path

from enterprise_agent.agent.runtime import Runtime
from enterprise_agent.agent.trace import DEFAULT_TRACE_PATH
from enterprise_agent.eval.common import dump_json, read_jsonl


def run_eval_tasks(
    eval_file: str | Path,
    limit: int | None = None,
    trace_file: str | Path = DEFAULT_TRACE_PATH,
) -> dict:
    tasks = read_jsonl(eval_file)
    selected_tasks = tasks[:limit] if limit is not None else tasks
    runtime = Runtime(trace_path=trace_file)
    executed = 0
    for task in selected_tasks:
        runtime.run(
            str(task.get("query", "")),
            user_role=str(task.get("user_role", "employee")),
            task_id=str(task.get("id")),
        )
        executed += 1
    return {
        "total": len(tasks),
        "executed": executed,
        "trace_file": str(trace_file),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run eval tasks and write runtime traces.")
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--trace-file", default=str(DEFAULT_TRACE_PATH))
    args = parser.parse_args()
    print(dump_json(run_eval_tasks(args.eval_file, limit=args.limit, trace_file=args.trace_file)))


if __name__ == "__main__":
    main()

