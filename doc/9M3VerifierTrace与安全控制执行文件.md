# M3 Verifier、Trace 与安全控制执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 M2 Runtime 基础上加入权限校验、结果验证、失败处理和执行轨迹记录，使系统从“能跑”升级为“可控、可观测、可复盘”。

**Architecture:** M3 增加 `permission.py`、`verifier.py`、`retry.py`、`trace.py`，并改造 Runtime 执行链路。Runtime 在工具执行前做权限检查，在生成答案后做 verifier，在失败时触发 retry/fallback/refusal，最后写入 `logs/traces.jsonl`。

**Tech Stack:** Python, JSONL trace, pytest, rule-based verifier。

---

## 1. 本阶段边界

本阶段必须完成：

* `employee/manager/admin` 三类角色；
* 工具级权限校验；
* `missing_citation`、`retrieval_empty`、`sql_error`、`permission_denied`、`format_error` 校验；
* 基础 retry/fallback/refusal；
* 每次请求写入一条 trace。

本阶段不做：

* 生产级 RBAC；
* 字段级脱敏；
* LLM-as-Judge；
* 真实人工审批流。

---

## 2. 文件清单

创建：

```text
enterprise_agent/
├── agent/
│   ├── permission.py
│   ├── verifier.py
│   ├── retry.py
│   └── trace.py
├── logs/
│   └── traces.jsonl
└── tests/
    ├── test_permission.py
    ├── test_verifier.py
    ├── test_trace.py
    └── test_runtime_m3.py
```

修改：

```text
enterprise_agent/agent/runtime.py
enterprise_agent/agent/state.py
enterprise_agent/tools/base.py
README.md
```

---

## 3. 执行任务

### Task 1: 实现 Permission

文件：`enterprise_agent/agent/permission.py`

- [ ] 定义角色：

```text
employee
manager
admin
```

- [ ] 定义工具权限矩阵：

```text
search_kb       employee manager admin
generate_report employee manager admin
workflow_check  employee manager admin
parse_doc       employee manager admin
query_sql       manager  admin
```

- [ ] 实现：

```python
def check_permission(user_role: str, tool) -> dict:
    ...
```

- [ ] 权限不足返回：

```python
{
    "allowed": False,
    "error_type": "permission_denied",
    "message": "当前角色无权调用 query_sql"
}
```

### Task 2: 实现 Verifier

文件：`enterprise_agent/agent/verifier.py`

- [ ] 实现：

```python
def verify(state) -> dict:
    ...
```

- [ ] 检查规则：

```text
RAG 任务 retrieved_docs 为空 -> retrieval_empty
需要引用但 answer 不包含 source 或 chunk_id -> missing_citation
query_sql 工具 status != success -> sql_error
permission_denied 后仍执行工具 -> permission_violation
report_generation 输出不含标题 -> format_error
```

- [ ] 输出格式：

```python
{
    "pass": False,
    "issues": [{"type": "missing_citation", "message": "回答缺少引用来源"}],
    "suggested_action": "retry_with_citation"
}
```

### Task 3: 实现 Retry / Fallback

文件：`enterprise_agent/agent/retry.py`

- [ ] 实现：

```python
def decide_next_action(verifier_result: dict) -> str:
    ...
```

- [ ] 规则：

```text
missing_citation -> retry_with_citation
retrieval_empty -> fallback_insufficient_evidence
sql_error -> fallback_without_data_claim
permission_denied -> refusal
format_error -> retry_with_format
permission_violation -> refusal
```

- [ ] Runtime 中最多 retry 一次，避免循环。

### Task 4: 实现 Trace Logger

文件：`enterprise_agent/agent/trace.py`

- [ ] 实现：

```python
def write_trace(state, path: str = "enterprise_agent/logs/traces.jsonl") -> str:
    ...
```

- [ ] 每条 trace 包含：

```python
{
    "task_id": "uuid",
    "timestamp": "...",
    "query": "...",
    "user_role": "employee",
    "task_type": "knowledge_qa",
    "plan": [],
    "tool_calls": [],
    "retrieved_docs": [],
    "tool_outputs": {},
    "answer": "...",
    "verifier_result": {},
    "success": True,
    "latency": 2.31,
    "error_type": None
}
```

### Task 5: 改造 Runtime

文件：`enterprise_agent/agent/runtime.py`

- [ ] 工具执行前调用 `check_permission`。
- [ ] 权限不足时不执行工具，写入 `errors` 和 `tool_calls`。
- [ ] 答案生成后调用 `verify`。
- [ ] verifier 失败后调用 `decide_next_action`。
- [ ] 根据 action 执行：

```text
retry_with_citation -> 重新生成含引用答案
fallback_insufficient_evidence -> 输出证据不足
fallback_without_data_claim -> 不生成数据结论
refusal -> 明确拒绝
retry_with_format -> 按报告模板重写
```

- [ ] 每次请求结束时调用 `write_trace`。

### Task 6: 测试

- [ ] `test_permission.py` 覆盖 employee 无法调用 query_sql。
- [ ] `test_verifier.py` 覆盖 missing_citation、retrieval_empty、sql_error。
- [ ] `test_trace.py` 覆盖 trace 字段完整性。
- [ ] `test_runtime_m3.py` 覆盖权限拒绝和 trace 写入。

---

## 4. 验收标准

运行：

```bash
python -m enterprise_agent.app --query "我是普通员工，帮我查询所有部门采购金额统计。" --role employee
python -m enterprise_agent.app --query "差旅报销需要哪些材料？" --role employee
pytest enterprise_agent/tests/test_permission.py enterprise_agent/tests/test_verifier.py enterprise_agent/tests/test_trace.py enterprise_agent/tests/test_runtime_m3.py -q
```

期望：

* 普通员工查询跨部门数据返回 `permission_denied`；
* RAG 回答包含引用来源；
* 每次请求写入 `enterprise_agent/logs/traces.jsonl`；
* trace 包含 `query/plan/tool_calls/retrieved_docs/answer/success/latency/error_type`。

---

## 5. 同步记录

```text
日期：
执行人：
完成步骤：
生成文件：
验证命令：
验证结果：
阻塞问题：
下一步：
```
