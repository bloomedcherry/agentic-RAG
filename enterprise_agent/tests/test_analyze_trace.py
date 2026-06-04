import json

from enterprise_agent.eval.analyze_trace import analyze_traces


def _write_jsonl(path, records):
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def test_analyze_traces_ignores_none_suggested_action_for_retry_rate(tmp_path):
    trace_file = tmp_path / "traces.jsonl"
    report_file = tmp_path / "eval_summary.md"
    _write_jsonl(
        trace_file,
        [
            {
                "task_id": "task_001",
                "task_type": "policy_qa",
                "tool_calls": [{"name": "search_kb", "status": "success"}],
                "error_type": None,
                "latency": 0.1,
                "verifier_result": {"pass": True, "suggested_action": "none"},
            },
            {
                "task_id": "task_002",
                "task_type": "policy_qa",
                "tool_calls": [{"name": "search_kb", "status": "success"}],
                "error_type": "missing_citation",
                "latency": 0.2,
                "verifier_result": {"pass": True, "suggested_action": "retry_with_citation"},
            },
            {
                "task_id": "task_003",
                "task_type": "data_analysis",
                "tool_calls": [{"name": "query_sql", "status": "error"}],
                "error_type": "sql_error",
                "latency": 0.3,
                "verifier_result": {"pass": False, "suggested_action": "fallback_without_data_claim"},
            },
        ],
    )

    metrics = analyze_traces(trace_file, report_path=report_file)

    assert metrics["retry_success_rate"] == 0.5
    assert report_file.exists()
