# M4 Eval、Demo 与项目总结执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建测试集和评估脚本，基于 trace 统计 RAG、工具调用、端到端任务、延迟和错误分布，并整理 README 与项目复盘材料。

**Architecture:** M4 不新增核心 Runtime 能力，而是围绕 `data/eval_tasks.jsonl`、`logs/traces.jsonl` 和 `eval/*.py` 建立评估闭环。评估脚本读取固定格式 eval set 和 trace，输出指标表和失败案例。

**Tech Stack:** Python, JSONL, pytest, pandas optional, Markdown report。

---

## 1. 本阶段边界

本阶段必须完成：

* 构造至少 50 条测试任务；
* 实现 `eval_rag.py`、`eval_tool.py`、`eval_task.py`、`analyze_trace.py`；
* 跑一轮 eval 并生成指标；
* README 包含运行命令、示例问题、trace 示例和评估结果；
* 输出项目总结和简历 bullet 草稿。

本阶段不做：

* 编造实验提升数值；
* LLM-as-Judge；
* 生产级监控平台；
* 复杂消融自动化平台。

---

## 2. 文件清单

创建：

```text
enterprise_agent/
├── data/
│   └── eval_tasks.jsonl
├── eval/
│   ├── __init__.py
│   ├── run_eval_tasks.py
│   ├── eval_rag.py
│   ├── eval_tool.py
│   ├── eval_task.py
│   └── analyze_trace.py
├── report/
│   ├── eval_summary.md
│   └── project_review.md
└── tests/
    ├── test_eval_rag.py
    ├── test_eval_tool.py
    └── test_eval_task.py
```

修改：

```text
README.md
doc/6简历 STAR 表达.md
```

---

## 3. 执行任务

### Task 1: 构建 Eval Set

文件：`enterprise_agent/data/eval_tasks.jsonl`

- [ ] 构造至少 50 条任务，分布：

```text
企业制度问答：15 条
流程判断：10 条
项目资料分析：10 条
数据分析：10 条
报告生成：5 条
```

- [ ] 每条任务格式：

```json
{
  "id": "task_001",
  "query": "差旅报销需要哪些材料？",
  "user_role": "employee",
  "expected_task_type": "knowledge_qa",
  "expected_tools": ["search_kb"],
  "gold_docs": ["policy_reimbursement.md"],
  "expected_answer_points": ["发票", "审批单", "行程证明"],
  "risk_level": "low",
  "need_citation": true,
  "need_sql": false,
  "need_human_approval": false
}
```

### Task 2: 实现 eval_rag.py

文件：`enterprise_agent/eval/eval_rag.py`

- [ ] 输入 `enterprise_agent/data/eval_tasks.jsonl`。
- [ ] 对包含 `gold_docs` 的任务调用 `retrieve(query, top_k=5)`。
- [ ] 输出：

```python
{
    "rag_recall_at_1": 0.0,
    "rag_recall_at_3": 0.0,
    "rag_recall_at_5": 0.0,
    "total": 0,
    "missed_cases": []
}
```

- [ ] 支持 CLI：

```bash
python -m enterprise_agent.eval.eval_rag --eval-file enterprise_agent/data/eval_tasks.jsonl
```

### Task 3: 实现 run_eval_tasks.py

文件：`enterprise_agent/eval/run_eval_tasks.py`

- [ ] 输入 `enterprise_agent/data/eval_tasks.jsonl`。
- [ ] 逐条调用 `Runtime.run(query, user_role)`。
- [ ] 每次调用由 Runtime 写入 `enterprise_agent/logs/traces.jsonl`。
- [ ] 支持 CLI：

```bash
python -m enterprise_agent.eval.run_eval_tasks --eval-file enterprise_agent/data/eval_tasks.jsonl --limit 50
```

- [ ] 输出执行摘要：

```python
{
    "total": 50,
    "executed": 50,
    "trace_file": "enterprise_agent/logs/traces.jsonl"
}
```

### Task 4: 实现 eval_tool.py

文件：`enterprise_agent/eval/eval_tool.py`

- [ ] 输入 `enterprise_agent/logs/traces.jsonl` 和 `enterprise_agent/data/eval_tasks.jsonl`。
- [ ] 统计：

```text
Tool Call Accuracy
Tool Success Rate
Permission Blocking Accuracy
wrong_tool_cases
```

- [ ] 判断逻辑：

```text
actual_tools = trace.tool_calls[].tool_name
expected_tools = eval_task.expected_tools
actual_tools 覆盖 expected_tools -> 工具选择正确
tool_call.status == success -> 工具执行成功
expected permission_denied 且 trace.error_type == permission_denied -> 权限拦截正确
```

### Task 5: 实现 eval_task.py

文件：`enterprise_agent/eval/eval_task.py`

- [ ] 统计：

```text
Task Success Rate
Citation Accuracy
Verifier Pass Rate
Average Latency
```

- [ ] 成功判定：

```text
task_type == expected_task_type
expected_tools 均被调用
answer 非空
need_citation=true 时 answer 包含 retrieved_docs 中的 source 或 chunk_id
verifier_result.pass == true
```

### Task 6: 实现 analyze_trace.py

文件：`enterprise_agent/eval/analyze_trace.py`

- [ ] 统计：

```text
task_type_distribution
tool_call_distribution
error_type_distribution
retry_success_rate
latency_breakdown
```

- [ ] 输出 Markdown 到 `enterprise_agent/report/eval_summary.md`。

### Task 7: 跑通评估

- [ ] 执行 50 条任务，生成 trace：

```bash
python -m enterprise_agent.eval.run_eval_tasks --eval-file enterprise_agent/data/eval_tasks.jsonl --limit 50
```

- [ ] 执行：

```bash
python -m enterprise_agent.eval.eval_rag --eval-file enterprise_agent/data/eval_tasks.jsonl
python -m enterprise_agent.eval.eval_tool --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
python -m enterprise_agent.eval.eval_task --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
python -m enterprise_agent.eval.analyze_trace --trace-file enterprise_agent/logs/traces.jsonl
```

### Task 8: 整理 README

文件：`README.md`

- [ ] 补充项目介绍：

```text
企业 Agentic RAG 知识助手与可控执行 Harness 系统
```

- [ ] 补充运行命令：

```bash
python -m enterprise_agent.rag.build_index
python -m enterprise_agent.data.init_business_db
python -m enterprise_agent.app --query "差旅报销需要哪些材料？" --role employee
python -m enterprise_agent.eval.eval_task --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
```

- [ ] 补充示例 trace 和指标表。没有实测数值时写明“评估尚未运行”，不得写提升百分比。

### Task 9: 输出项目复盘

文件：`enterprise_agent/report/project_review.md`

- [ ] 包含：

```text
项目目标
架构设计
RAG 子系统
Tool Contract / Registry
Harness Runtime
Verifier / Retry
Trace Logging
Eval 结果
失败案例
后续扩展
```

### Task 10: 更新简历表达

文件：`doc/6简历 STAR 表达.md`

- [ ] 如果已经跑出真实指标，补充实测值。
- [ ] 如果没有真实指标，只写“构建评估体系”和“设计消融实验”，不写具体提升。

---

## 4. 验收标准

运行：

```bash
python -m enterprise_agent.eval.eval_rag --eval-file enterprise_agent/data/eval_tasks.jsonl
python -m enterprise_agent.eval.eval_tool --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
python -m enterprise_agent.eval.eval_task --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
python -m enterprise_agent.eval.analyze_trace --trace-file enterprise_agent/logs/traces.jsonl
pytest enterprise_agent/tests/test_eval_rag.py enterprise_agent/tests/test_eval_tool.py enterprise_agent/tests/test_eval_task.py -q
```

期望：

* `eval_tasks.jsonl` 至少 50 条；
* eval 脚本输出指标；
* `report/eval_summary.md` 存在；
* README 能指导用户从构建索引到跑评估；
* 没有未验证的提升数字。

---

## 5. 同步记录

```text
日期：2026-06-03
执行人：Codex
完成步骤：
- 构建 50 条 eval task，覆盖制度问答、流程判断、项目分析、数据分析和报告生成。
- 实现 enterprise_agent.eval 包，包括 run_eval_tasks.py、eval_rag.py、eval_tool.py、eval_task.py、analyze_trace.py。
- 修复 Runtime.run(task_id=...) 在 LangGraph state 中丢失的问题，使 eval trace 可和任务集对齐。
- 修复 eval_tool/eval_task 在追加 traces.jsonl 场景下重复统计历史同 task_id trace 的问题。
- 生成 eval_summary.md 和 project_review.md。
- 更新 README 与简历表达。
生成文件：
- enterprise_agent/data/eval_tasks.jsonl
- enterprise_agent/eval/__init__.py
- enterprise_agent/eval/common.py
- enterprise_agent/eval/run_eval_tasks.py
- enterprise_agent/eval/eval_rag.py
- enterprise_agent/eval/eval_tool.py
- enterprise_agent/eval/eval_task.py
- enterprise_agent/eval/analyze_trace.py
- enterprise_agent/report/eval_summary.md
- enterprise_agent/report/project_review.md
- enterprise_agent/tests/test_eval_rag.py
- enterprise_agent/tests/test_eval_tool.py
- enterprise_agent/tests/test_eval_task.py
- enterprise_agent/tests/test_analyze_trace.py
验证命令：
- /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests/test_eval_rag.py enterprise_agent/tests/test_eval_tool.py enterprise_agent/tests/test_eval_task.py enterprise_agent/tests/test_analyze_trace.py -q
- /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.run_eval_tasks --eval-file enterprise_agent/data/eval_tasks.jsonl --limit 50
- /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.eval_rag --eval-file enterprise_agent/data/eval_tasks.jsonl
- /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.eval_tool --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
- /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.eval_task --trace-file enterprise_agent/logs/traces.jsonl --eval-file enterprise_agent/data/eval_tasks.jsonl
- /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.analyze_trace --trace-file enterprise_agent/logs/traces.jsonl
验证结果：
- Eval set: 50 条。
- RAG Recall@1/3/5: 0.075 / 0.100 / 0.100。
- Tool Call Accuracy: 1.000。
- Tool Success Rate: 0.978。
- Permission Blocking Accuracy: 1.000。
- Task Success Rate: 0.960。
- Citation Accuracy: 1.000。
- Verifier Pass Rate: 0.960。
- Average Latency: 0.624527s。
阻塞问题：
- 无。
下一步：
- 优化 RAG 检索，考虑 hybrid retrieval、embedding 和 rerank。
- 将权限拒绝类任务拆成安全成功指标，避免和普通任务成功率混淆。
- 增加更丰富的受控 SQL query_type。
```
