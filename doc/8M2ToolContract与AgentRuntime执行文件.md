# M2 Tool Contract 与 Agent Runtime 执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 RAG、SQL、流程校验和报告生成封装为统一工具，并跑通单 Supervisor Agent 的主执行流程。

**Architecture:** M2 在 M1 的 RAG 子系统基础上增加 `BaseTool`、`ToolRegistry`、`AgentState`、`Planner`、`Router`、`ContextBuilder` 和 `Runtime`。第一版 Runtime 可以是顺序执行，也可以预留 `agent/graph.py` 给 LangGraph，但不强制引入复杂图编排。

**Tech Stack:** Python, pydantic/dataclasses, sqlite3, pytest, optional LangGraph。

---

## 1. 本阶段边界

本阶段必须完成：

* `tools/base.py` 定义 Tool Contract；
* `tools/registry.py` 注册和查询工具；
* `tools/search_kb.py` 接入 M1 retriever；
* `tools/query_sql.py` 使用受控 query_type 查询 `business.db`；
* `tools/workflow_check.py` 根据规则返回流程判断；
* `tools/generate_report.py` 生成结构化 Markdown 草稿；
* `agent/runtime.py` 跑通用户请求到最终回答。

本阶段不做：

* 完整 Verifier；
* Retry 策略；
* 复杂权限系统；
* Eval 指标统计。

---

## 2. 文件清单

创建：

```text
enterprise_agent/
├── app.py
├── agent/
│   ├── __init__.py
│   ├── state.py
│   ├── planner.py
│   ├── router.py
│   ├── context_builder.py
│   ├── runtime.py
│   └── graph.py
├── tools/
│   ├── base.py
│   ├── registry.py
│   ├── search_kb.py
│   ├── query_sql.py
│   ├── workflow_check.py
│   └── generate_report.py
├── data/
│   ├── business.db
│   └── workflow_rules.json
└── tests/
    ├── test_tools.py
    ├── test_planner_router.py
    └── test_runtime.py
```

修改：

```text
README.md
requirements.txt
```

---

## 3. 执行任务

### Task 1: 实现 Tool Contract

文件：`enterprise_agent/tools/base.py`

- [ ] 定义 `BaseTool`：

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    status: str
    output: dict[str, Any]
    error: str | None = None
    latency: float = 0.0


class BaseTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permission: str
    risk_level: str
    timeout: int
    retry_policy: dict[str, Any]

    def run(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError
```

### Task 2: 实现 Tool Registry

文件：`enterprise_agent/tools/registry.py`

- [ ] 实现 `ToolRegistry.register(tool)`、`get(name)`、`list_tools()`。
- [ ] 注册工具时检查 `name` 不为空且不重复。
- [ ] `list_tools()` 返回工具元信息，至少包含 `name/description/permission/risk_level/input_schema`。

### Task 3: 封装 search_kb

文件：`enterprise_agent/tools/search_kb.py`

- [ ] 实现 `SearchKBTool(BaseTool)`。
- [ ] `run(query: str, top_k: int = 5, filters: dict | None = None)` 调用 `rag.retriever.retrieve`。
- [ ] 输出：

```python
{
    "retrieved_docs": [
        {"source": "...", "chunk_id": "...", "content": "...", "score": 0.82}
    ]
}
```

### Task 4: 构建业务数据库

文件：`enterprise_agent/data/business.db`

- [ ] 创建 `projects`、`expenses`、`purchase_requests` 三张表。
- [ ] 插入至少 5 条项目数据、10 条报销数据、10 条采购申请数据。
- [ ] 提供初始化脚本 `enterprise_agent/data/init_business_db.py`。

### Task 5: 实现 query_sql

文件：`enterprise_agent/tools/query_sql.py`

- [ ] 实现受控查询，不允许模型自由传入 SQL。
- [ ] 支持：

```text
project_status
expense_summary
purchase_check
```

- [ ] 输出 `rows` 和 `summary`。

### Task 6: 实现 workflow_check

文件：`enterprise_agent/tools/workflow_check.py`

- [ ] 读取 `enterprise_agent/data/workflow_rules.json`。
- [ ] 支持 `process_type=purchase`、`amount`、`department`、`user_role`。
- [ ] 返回：

```python
{
    "decision": "need_manager_approval",
    "reason": "采购金额 8000 元超过部门负责人审批阈值 5000 元",
    "required_approval": ["department_manager"]
}
```

### Task 7: 实现 generate_report

文件：`enterprise_agent/tools/generate_report.py`

- [ ] 第一版使用模板生成 Markdown，不依赖 LLM。
- [ ] 输入 `task_type/evidence/tool_outputs/format`。
- [ ] 输出包含标题、摘要、依据、待办或风险。

### Task 8: 实现 Agent State

文件：`enterprise_agent/agent/state.py`

- [ ] 定义状态字段：

```python
query: str
user_role: str
task_type: str | None
plan: list[str]
tool_calls: list[dict]
retrieved_docs: list[dict]
tool_outputs: dict
answer: str
errors: list[dict]
latency: float
```

### Task 9: 实现 Planner / Router

文件：

```text
enterprise_agent/agent/planner.py
enterprise_agent/agent/router.py
```

- [ ] Planner 使用规则分类：

```text
报销、采购、合同、制度 -> knowledge_qa
审批、是否需要、流程 -> workflow_query
项目、风险、进展、待办 -> project_analysis
数据、统计、下降、增长 -> data_analysis
生成、报告、周报、总结 -> report_generation
```

- [ ] Router 根据 task_type 返回工具列表：

```text
knowledge_qa -> search_kb
workflow_query -> search_kb + workflow_check
project_analysis -> search_kb + generate_report
data_analysis -> query_sql + generate_report
report_generation -> search_kb + generate_report
```

### Task 10: 实现 Context Builder

文件：`enterprise_agent/agent/context_builder.py`

- [ ] 将 `query`、`user_role`、`plan`、`retrieved_docs`、`tool_outputs` 组装成固定结构。
- [ ] 加入约束：

```text
必须基于证据和工具结果回答。
如果证据不足，说明无法确认。
回答需要包含引用来源。
```

### Task 11: 实现 Runtime 和 CLI

文件：

```text
enterprise_agent/agent/runtime.py
enterprise_agent/app.py
```

- [ ] `Runtime.run(query: str, user_role: str = "employee") -> dict`。
- [ ] 执行顺序：

```text
state -> planner -> router -> tools -> context_builder -> answer
```

- [ ] `app.py` 支持：

```bash
python -m enterprise_agent.app --query "差旅报销需要哪些材料？" --role employee
```

---

## 4. 验收标准

运行：

```bash
python -m enterprise_agent.data.init_business_db
python -m enterprise_agent.app --query "差旅报销需要哪些材料？" --role employee
python -m enterprise_agent.app --query "这个 8000 元采购申请是否需要审批？" --role employee
python -m enterprise_agent.app --query "帮我分析 A 项目当前有哪些风险。" --role manager
pytest enterprise_agent/tests/test_tools.py enterprise_agent/tests/test_planner_router.py enterprise_agent/tests/test_runtime.py -q
```

期望：

* 制度问答调用 `search_kb`；
* 流程判断调用 `search_kb + workflow_check`；
* 项目分析调用 `search_kb + generate_report`；
* Runtime 输出包含 `answer`、`task_type`、`tool_calls`。

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
