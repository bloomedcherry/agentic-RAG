import json

from enterprise_agent.eval.eval_task import evaluate_tasks


def _write_jsonl(path, records):
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def test_evaluate_tasks_counts_success_citation_verifier_and_latency(tmp_path):
    eval_file = tmp_path / "eval_tasks.jsonl"
    trace_file = tmp_path / "traces.jsonl"
    _write_jsonl(
        eval_file,
        [
            {
                "id": "task_001",
                "expected_task_type": "policy_qa",
                "expected_tools": ["search_kb"],
                "need_citation": True,
            },
            {
                "id": "task_002",
                "expected_task_type": "data_analysis",
                "expected_tools": ["query_sql"],
                "need_citation": False,
            },
        ],
    )
    _write_jsonl(
        trace_file,
        [
            {
                "task_id": "task_001",
                "task_type": "policy_qa",
                "tool_calls": [{"name": "search_kb", "status": "success"}],
                "retrieved_docs": [{"source": "policy_025.md", "chunk_id": "p1"}],
                "answer": "结论。\n来源：policy_025.md",
                "verifier_result": {"pass": True, "issues": []},
                "latency": 0.2,
            },
            {
                "task_id": "task_002",
                "task_type": "data_analysis",
                "tool_calls": [{"name": "query_sql", "status": "success"}],
                "retrieved_docs": [],
                "answer": "# 分析草稿",
                "verifier_result": {"pass": False, "issues": [{"type": "format_error"}]},
                "latency": 0.4,
            },
        ],
    )

    metrics = evaluate_tasks(trace_file, eval_file)

    assert metrics["total"] == 2
    assert metrics["task_success_rate"] == 0.5
    assert metrics["citation_accuracy"] == 1.0
    assert metrics["verifier_pass_rate"] == 0.5
    assert metrics["average_latency"] == 0.3
    assert metrics["failed_cases"] == [
        {
            "id": "task_002",
            "query": "",
            "reasons": ["verifier_failed"],
        }
    ]


def test_evaluate_tasks_uses_latest_trace_per_task(tmp_path):
    eval_file = tmp_path / "eval_tasks.jsonl"
    trace_file = tmp_path / "traces.jsonl"
    _write_jsonl(
        eval_file,
        [
            {
                "id": "task_001",
                "expected_task_type": "policy_qa",
                "expected_tools": ["search_kb"],
                "need_citation": False,
            }
        ],
    )
    _write_jsonl(
        trace_file,
        [
            {
                "task_id": "task_001",
                "task_type": "data_analysis",
                "tool_calls": [],
                "answer": "",
                "verifier_result": {"pass": False},
                "latency": 0.1,
            },
            {
                "task_id": "task_001",
                "task_type": "policy_qa",
                "tool_calls": [{"name": "search_kb", "status": "success"}],
                "answer": "结论",
                "verifier_result": {"pass": True},
                "latency": 0.3,
            },
        ],
    )

    metrics = evaluate_tasks(trace_file, eval_file)

    assert metrics["total"] == 1
    assert metrics["task_success_rate"] == 1.0
    assert metrics["average_latency"] == 0.3
