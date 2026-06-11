# Harness Engineering Agent Demo

This repository contains an enterprise Agentic RAG knowledge assistant and controllable Agent Harness runtime.

## M1: Data And RAG Baseline

Run the first milestone with:

```bash
python -m enterprise_agent.rag.download_raw_data
python -m enterprise_agent.rag.data_builder --min-docs 300
python -m enterprise_agent.rag.build_index
python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
```

Use the project conda environment:

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.download_raw_data
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.data_builder --min-docs 300
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.build_index
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
```

The M1 scope downloads a small set of public Chinese seed documents, expands them into a medium-size enterprise corpus, chunks documents, writes index metadata, and runs top-k retrieval. It supports Markdown, TXT, PDF, DOCX, and HTML parsing. It does not include Planner, Tool Contract, LLM answer generation, Verifier, Retry, or Eval yet.

## M2: Tool Contract And LangGraph Runtime

Initialize business data and run the CLI:

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.data.init_business_db
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app --query "差旅报销需要哪些材料？" --role employee
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app --query "这个 8000 元采购申请是否需要审批？" --role employee
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app --query "统计当前高风险项目" --role manager
```

M2 adds the framework-neutral tool contract, tool registry, LangGraph runtime, rule-based planner/router, context builder, template answer generation, and controlled tools:

```text
search_kb
workflow_check
query_sql
generate_report
```

The runtime entry point is:

```python
from enterprise_agent.agent.runtime import Runtime

result = Runtime().run("差旅报销需要哪些材料？", user_role="employee")
```

## M3: Verifier, Trace, And Safety Controls

M3 adds role-based tool permissions, rule-based verifier, retry/fallback decisions, and JSONL trace logging. Supported roles are:

```text
employee
manager
admin
```

`employee` can use knowledge, workflow, and report tools, but cannot call `query_sql`. `manager` and `admin` can call `query_sql`.

Each `Runtime.run()` writes one trace record to:

```text
enterprise_agent/logs/traces.jsonl
```

The trace file is a generated local artifact and is ignored by git. Tests can inject a temporary trace path:

```python
runtime = Runtime(trace_path="/tmp/traces.jsonl")
```

Run M3 verification:

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests/test_permission.py enterprise_agent/tests/test_verifier.py enterprise_agent/tests/test_trace.py enterprise_agent/tests/test_runtime_m3.py -q
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests -q
```

## M4: Eval, Demo, And Project Review

M4 adds a 50-task eval set, eval scripts, trace analysis, and project review reports.

Run the full demo path:

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.build_index
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.data.init_business_db
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app --query "差旅报销需要哪些材料？" --role employee
```

Run eval tasks and metrics:

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.run_eval_tasks --eval-file enterprise_agent/data/eval_tasks.jsonl --limit 50
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.eval_rag --eval-file enterprise_agent/data/eval_tasks.jsonl
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.eval_tool --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.eval_task --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.analyze_trace --trace-file enterprise_agent/logs/traces.jsonl
```

Example trace fields:

```json
{
  "task_id": "task_001",
  "query": "差旅报销需要哪些材料？",
  "user_role": "employee",
  "task_type": "policy_qa",
  "tool_calls": [{"name": "search_kb", "status": "success"}],
  "verifier_result": {"pass": true, "issues": [], "suggested_action": "none"},
  "success": true,
  "error_type": null
}
```

Latest measured eval results:

| Metric | Value |
| --- | ---: |
| RAG Recall@1 | 0.075 |
| RAG Recall@3 | 0.100 |
| RAG Recall@5 | 0.100 |
| Tool Call Accuracy | 1.000 |
| Tool Success Rate | 0.978 |
| Permission Blocking Accuracy | 1.000 |
| Task Success Rate | 0.960 |
| Citation Accuracy | 1.000 |
| Verifier Pass Rate | 0.960 |
| Average Latency | 0.624527s |

Reports:

```text
enterprise_agent/report/eval_summary.md
enterprise_agent/report/project_review.md
```

## M5: Unified Configuration And LLM Gateway

M5 adds an optional OpenAI-compatible LLM layer while retaining the M4 rule
planner, template answer generator, permission checks, verifier, and trace path
as deterministic fallbacks.

Copy `.env.example` to `.env` and configure model names and endpoints. The main
model generates answers. The independently configured utility model performs
planning. Both local vLLM and third-party OpenAI-compatible APIs use the same
gateway; no model name is hardcoded in application code.

Run without an LLM:

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "差旅报销需要哪些材料？" --role employee --no-llm
```

Run with configured LLM endpoints:

```bash
LLM_ENABLED=true \
MAIN_LLM_BASE_URL=http://127.0.0.1:8000/v1 \
MAIN_LLM_API_KEY=local \
MAIN_LLM_MODEL=<configured-model> \
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "差旅报销需要哪些材料？" --role employee
```

`--llm-enabled` and `--no-llm` override `LLM_ENABLED` for one CLI invocation.
If an endpoint is unavailable or produces invalid planning output, the runtime
falls back to the M4 path. Trace records include model, endpoint, token counts,
latency, status, error type, and fallback state without storing prompts or API
keys.
