# Harness Engineering Agent Demo

This repository contains an enterprise Agentic RAG demo built around an Agent Harness runtime.

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
