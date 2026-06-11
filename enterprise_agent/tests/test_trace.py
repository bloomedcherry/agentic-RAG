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
        "llm_calls": [
            {
                "purpose": "planner",
                "provider": "openai_compatible",
                "model": "utility-model",
                "endpoint": "primary",
                "status": "success",
                "error_type": None,
                "prompt_version": "m5-planner-v1",
                "prompt_tokens": 20,
                "completion_tokens": 8,
                "latency": 0.03,
                "messages": [{"role": "user", "content": "sensitive full prompt"}],
                "api_key": "top-secret",
                "Authorization": "Bearer top-secret",
            }
        ],
        "llm_fallback_used": False,
        "prompt_version": "m5-planner-v1",
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
        "llm_calls",
        "llm_fallback_used",
        "prompt_version",
    ]:
        assert key in record
    assert record["query"] == state["query"]
    assert record["user_role"] == "employee"
    assert record["success"] is True
    assert record["error_type"] is None
    assert record["llm_calls"][0]["model"] == "utility-model"
    serialized = json.dumps(record, ensure_ascii=False)
    assert "sensitive full prompt" not in serialized
    assert "top-secret" not in serialized
    assert "Authorization" not in serialized


def test_trace_distinguishes_fallback_endpoint_and_rule_fallback(tmp_path):
    trace_path = tmp_path / "traces.jsonl"
    state = {
        "query": "差旅报销需要哪些材料？",
        "role": "employee",
        "task_type": "policy_qa",
        "answer": "结论。\n来源：policy.md",
        "verifier_result": {"pass": True, "issues": []},
        "llm_calls": [
            {
                "purpose": "planner",
                "provider": "openai_compatible",
                "model": "fallback-model",
                "endpoint": "fallback",
                "status": "success",
                "error_type": None,
                "prompt_version": "m5-planner-v1",
                "prompt_tokens": 12,
                "completion_tokens": 4,
                "latency": 0.2,
            }
        ],
        "llm_fallback_used": True,
        "prompt_version": "m5-planner-v1",
    }

    write_trace(state, path=trace_path)

    record = json.loads(trace_path.read_text(encoding="utf-8"))
    assert record["llm_calls"][0]["endpoint"] == "fallback"
    assert record["llm_calls"][0]["model"] == "fallback-model"
    assert record["llm_fallback_used"] is True
