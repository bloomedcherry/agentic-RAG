import json

from enterprise_agent.agent.runtime import Runtime
from enterprise_agent.tests.test_runtime import _prepare_runtime_data


def test_runtime_denies_employee_sql_and_writes_trace(tmp_path):
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    trace_path = tmp_path / "traces.jsonl"
    runtime = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        trace_path=trace_path,
    )

    result = runtime.run("我是普通员工，帮我查询所有部门采购金额统计。", user_role="employee")

    assert result["task_type"] == "data_analysis"
    assert result["tool_calls"] == [{"name": "query_sql", "status": "permission_denied"}]
    assert result["errors"][0]["type"] == "permission_denied"
    assert "无权调用 query_sql" in result["answer"]
    assert result["verifier_result"]["pass"] is False
    assert result["verifier_result"]["suggested_action"] == "refusal"

    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["query"] == result["query"]
    assert records[0]["error_type"] == "permission_denied"
    assert records[0]["success"] is False


def test_runtime_policy_answer_keeps_citation_and_trace_success(tmp_path):
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    trace_path = tmp_path / "traces.jsonl"

    result = Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        trace_path=trace_path,
    ).run("差旅报销需要哪些材料？", user_role="employee")

    assert result["verifier_result"]["pass"] is True
    assert "来源" in result["answer"]
    record = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])
    assert record["success"] is True
    assert record["error_type"] is None


def test_runtime_preserves_supplied_task_id_in_trace(tmp_path):
    index_dir, db_path, rules_path = _prepare_runtime_data(tmp_path)
    trace_path = tmp_path / "traces.jsonl"

    Runtime(
        index_dir=index_dir,
        db_path=db_path,
        workflow_rules_path=rules_path,
        trace_path=trace_path,
    ).run("差旅报销需要哪些材料？", user_role="employee", task_id="task_eval_001")

    record = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])
    assert record["task_id"] == "task_eval_001"
