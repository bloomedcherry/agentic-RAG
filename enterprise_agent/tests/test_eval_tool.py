import json

from enterprise_agent.eval.eval_tool import evaluate_tools


def _write_jsonl(path, records):
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def test_evaluate_tools_counts_accuracy_success_and_permission_blocks(tmp_path):
    eval_file = tmp_path / "eval_tasks.jsonl"
    trace_file = tmp_path / "traces.jsonl"
    _write_jsonl(
        eval_file,
        [
            {"id": "task_001", "expected_tools": ["search_kb"], "expected_error_type": None},
            {"id": "task_002", "expected_tools": ["query_sql"], "expected_error_type": "permission_denied"},
            {"id": "task_003", "expected_tools": ["search_kb", "generate_report"], "expected_error_type": None},
        ],
    )
    _write_jsonl(
        trace_file,
        [
            {
                "task_id": "task_001",
                "tool_calls": [{"name": "search_kb", "status": "success"}],
                "error_type": None,
            },
            {
                "task_id": "task_002",
                "tool_calls": [{"name": "query_sql", "status": "permission_denied"}],
                "error_type": "permission_denied",
            },
            {
                "task_id": "task_003",
                "tool_calls": [{"name": "search_kb", "status": "success"}],
                "error_type": "missing_citation",
            },
        ],
    )

    metrics = evaluate_tools(trace_file, eval_file)

    assert metrics["total"] == 3
    assert metrics["tool_call_accuracy"] == 2 / 3
    assert metrics["tool_success_rate"] == 2 / 4
    assert metrics["permission_blocking_accuracy"] == 1.0
    assert metrics["wrong_tool_cases"] == [
        {
            "id": "task_003",
            "expected_tools": ["search_kb", "generate_report"],
            "actual_tools": ["search_kb"],
        }
    ]


def test_evaluate_tools_uses_latest_trace_per_task(tmp_path):
    eval_file = tmp_path / "eval_tasks.jsonl"
    trace_file = tmp_path / "traces.jsonl"
    _write_jsonl(eval_file, [{"id": "task_001", "expected_tools": ["search_kb"]}])
    _write_jsonl(
        trace_file,
        [
            {"task_id": "task_001", "tool_calls": [], "error_type": "wrong_tool"},
            {
                "task_id": "task_001",
                "tool_calls": [{"name": "search_kb", "status": "success"}],
                "error_type": None,
            },
        ],
    )

    metrics = evaluate_tools(trace_file, eval_file)

    assert metrics["total"] == 1
    assert metrics["tool_call_accuracy"] == 1.0
