"""CLI entry point for the enterprise agent runtime."""

from __future__ import annotations

import argparse

from enterprise_agent.agent.runtime import Runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the enterprise agent demo.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--role", default="employee")
    parser.add_argument("--index-dir", default=None)
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--workflow-rules-path", default=None)
    parser.add_argument(
        "--user-id",
        default=None,
        help="Session owner. Production services must derive this from authentication.",
    )
    parser.add_argument("--thread-id", default=None, help="Conversation identifier.")
    llm_group = parser.add_mutually_exclusive_group()
    llm_group.add_argument(
        "--llm-enabled",
        dest="llm_enabled",
        action="store_true",
        help="Enable configured LLM clients for this invocation.",
    )
    llm_group.add_argument(
        "--no-llm",
        dest="llm_enabled",
        action="store_false",
        help="Use the deterministic rule and template path.",
    )
    parser.set_defaults(llm_enabled=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    runtime_kwargs = {"llm_enabled": args.llm_enabled}
    if args.index_dir:
        runtime_kwargs["index_dir"] = args.index_dir
    if args.db_path:
        runtime_kwargs["db_path"] = args.db_path
    if args.workflow_rules_path:
        runtime_kwargs["workflow_rules_path"] = args.workflow_rules_path

    result = Runtime(**runtime_kwargs).run(
        args.query,
        user_role=args.role,
        user_id=args.user_id,
        thread_id=args.thread_id,
    )
    print(f"user_id: {result.get('user_id')}")
    print(f"thread_id: {result.get('thread_id')}")
    print(f"task_type: {result.get('task_type')}")
    print(f"tool_calls: {result.get('tool_calls')}")
    print("answer:")
    print(result.get("answer", ""))


if __name__ == "__main__":
    main()
