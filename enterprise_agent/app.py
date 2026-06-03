"""CLI entry point for the enterprise agent runtime."""

from __future__ import annotations

import argparse

from enterprise_agent.agent.runtime import Runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the enterprise agent demo.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--role", default="employee")
    parser.add_argument("--index-dir", default=None)
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--workflow-rules-path", default=None)
    args = parser.parse_args()

    runtime_kwargs = {}
    if args.index_dir:
        runtime_kwargs["index_dir"] = args.index_dir
    if args.db_path:
        runtime_kwargs["db_path"] = args.db_path
    if args.workflow_rules_path:
        runtime_kwargs["workflow_rules_path"] = args.workflow_rules_path

    result = Runtime(**runtime_kwargs).run(args.query, user_role=args.role)
    print(f"task_type: {result.get('task_type')}")
    print(f"tool_calls: {result.get('tool_calls')}")
    print("answer:")
    print(result.get("answer", ""))


if __name__ == "__main__":
    main()
