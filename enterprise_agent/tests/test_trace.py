import json

from enterprise_agent.agent.trace import write_trace


def test_write_trace_appends_complete_jsonl_record(tmp_path):
    trace_path = tmp_path / "traces.jsonl"
    state = {
        "query": "差旅报销需要哪些材料？",
        "role": "employee",
        "task_type": "policy_qa",
        "plan": ["检索知识库"],
        "tool_calls": [{"name": "search_kb", "status": "success"}],
        "retrieved_docs": [{"source": "policy.md", "chunk_id": "c1"}],
        "tool_outputs": {"search_kb": {"documents": []}},
        "answer": "结论。\n来源：policy.md",
        "verifier_result": {"pass": True, "issues": []},
        "latency": 0.12,
        "errors": [],
    }

    written_path = write_trace(state, path=trace_path)

    assert written_path == str(trace_path)
    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    record = records[0]
    for key in [
        "task_id",
        "timestamp",
        "query",
        "user_role",
        "task_type",
        "plan",
        "tool_calls",
        "retrieved_docs",
        "tool_outputs",
        "answer",
        "verifier_result",
        "success",
        "latency",
        "error_type",
    ]:
        assert key in record
    assert record["query"] == state["query"]
    assert record["user_role"] == "employee"
    assert record["success"] is True
    assert record["error_type"] is None
