# M2 Tool Contract 与 Agent Runtime 执行报告

## 1. 阶段结论

M2 已完成最小可运行闭环：在 M1 RAG 基础上，引入项目自定义 Tool Contract、Tool Registry、LangGraph Runtime、规则型 Planner/Router、工具执行节点、Context Builder、模板答案生成和 CLI。

当前链路：

```text
用户 query
-> Runtime.run()
-> LangGraph StateGraph
-> planner_node
-> router_node
-> tool_executor_node
-> context_builder_node
-> answer_generator_node
-> CLI 输出
```

M2 当前是规则型单 Supervisor Agent，不接真实 LLM。Supervisor 的职责是识别任务类型、选择工具链、执行工具、汇总上下文并生成模板答案。

## 2. 实际落地文件

新增核心文件：

```text
enterprise_agent/
├── app.py
├── agent/
│   ├── __init__.py
│   ├── state.py
│   ├── planner.py
│   ├── router.py
│   ├── context_builder.py
│   ├── graph.py
│   └── runtime.py
├── tools/
│   ├── base.py
│   ├── registry.py
│   └── runtime_tools.py
├── data/
│   ├── __init__.py
│   ├── init_business_db.py
│   └── workflow_rules.json
└── tests/
    ├── test_init_business_db.py
    ├── test_tools.py
    ├── test_planner_router.py
    └── test_runtime.py
```

说明：

* 工具实现集中在 `enterprise_agent/tools/runtime_tools.py`，没有拆成 `search_kb.py/query_sql.py/workflow_check.py/generate_report.py` 四个文件。
* `business.db` 是本地生成文件，受 `.gitignore` 的 `*.db` 规则忽略，不作为源码提交。
* 未修改 `environment.yml`、`install_env_tmux.sh`，未恢复已删除的 `doc/1文档关系图.md`。

## 3. Tool Contract 与 Registry

`enterprise_agent/tools/base.py` 定义：

* `RetryPolicy`
* `ToolResult(status, output, error, latency)`
* `BaseTool`

`BaseTool` 暴露统一元信息：

```text
name
description
input_schema
output_schema
permission
risk_level
timeout
retry_policy
```

`BaseTool.execute()` 负责记录 latency，并把异常统一转换为 `ToolResult(status="error")`。

`enterprise_agent/tools/registry.py` 定义 `ToolRegistry`：

* `register(tool)`
* `get(name)`
* `list_metadata()`

注册时会拒绝空名称和重复名称。

## 4. 已实现工具

### search_kb

类：`SearchKbTool`

作用：封装 M1 TF-IDF retriever。

输入：

```text
query
top_k
filters
```

当前默认 `top_k=5`，在 `enterprise_agent/agent/graph.py` 的 `_tool_args()` 中固定：

```python
return {"query": query, "top_k": 5}
```

CLI 暂未暴露 `--top-k` 参数。

输出：

```text
documents
```

### query_sql

类：`QuerySqlTool`

作用：执行受控 SQL 查询，不允许自由 SQL。

当前支持：

```text
project_risks
high_risk_projects
```

查询字段：

```text
name
status
risk_level
owner
budget
source
milestone
risks
```

### workflow_check

类：`WorkflowCheckTool`

作用：读取 `workflow_rules.json`，根据流程类型和金额判断是否需要审批。

当前用于采购流程：

```text
workflow_type=purchase
amount=...
```

8000 元采购申请会返回需要部门经理审批。

### generate_report

类：`GenerateReportTool`

作用：基于工具输出生成 Markdown 草稿。

当前是模板生成，不接 LLM。报告会包含：

* 任务类型
* 用户问题
* 知识库证据或业务数据
* 初步结论和复核提示

## 5. LangGraph Runtime

入口：`enterprise_agent/agent/runtime.py`

调用方式：

```python
from enterprise_agent.agent.runtime import Runtime

runtime = Runtime()
result = runtime.run("差旅报销需要哪些材料？", user_role="employee")
```

返回主要字段：

```text
query
role
task_type
plan
selected_tools
tool_calls
retrieved_docs
tool_outputs
context
answer
errors
latency
```

图结构在 `enterprise_agent/agent/graph.py`：

```text
START
-> planner_node
-> router_node
-> tool_executor_node
-> context_builder_node
-> answer_generator_node
-> END
```

## 6. Planner / Router

Planner 位于 `enterprise_agent/agent/planner.py`，使用规则分类：

```text
policy_qa
workflow_check
project_analysis
data_analysis
```

Router 位于 `enterprise_agent/agent/router.py`，工具链如下：

```text
policy_qa        -> search_kb
workflow_check   -> search_kb + workflow_check
project_analysis -> search_kb + generate_report
data_analysis    -> query_sql + generate_report
```

## 7. 业务数据库构建方式

初始化脚本：`enterprise_agent/data/init_business_db.py`

当前 `business.db` 不再使用手写模拟 seed 数据。构建方式是规则解析现有项目文档：

```text
读取 enterprise_agent/data/docs/projects/project_*.md
-> 使用正则从 markdown 模板抽取字段
-> 写入 SQLite projects 表
```

解析字段：

```text
name       <- 标题，例如 "# A 项目档案 001"
owner      <- 项目背景中的 "由 xxx 牵头"
department <- 同 owner
budget     <- "当前预算基准约为 xxx 元"
milestone  <- "最近一个里程碑为 xxx"
risks      <- "当前风险包括 xxx"
source     <- 原始文档名，例如 "project_001.md"
status     <- 规则推断，当前项目档案默认 "进行中"
risk_level <- 规则推断，命中高风险/标红风险/预算消耗偏高/延期则为 "高"
```

真实构建结果：

```text
projects 表 80 行
来源：80 个 project_*.md
risks 字段非空
旧 A/B/C 三条硬编码样例已删除
```

生成命令：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.data.init_business_db
```

## 8. CLI 调用

项目根目录：

```bash
cd /mnt/sdc/zxuny/github/harness-engineering
```

初始化业务库：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.data.init_business_db
```

制度问答：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app --query "差旅报销需要哪些材料？" --role employee
```

示例输出：

```text
task_type: policy_qa
tool_calls: [{'name': 'search_kb', 'status': 'success'}]
answer:
结论：差旅报销通常需要提交以下材料：
- 行程单
- 发票
- 审批单
- 费用明细
- 付款账户
- 例外材料
来源：policy_025.md，policy_065.md，policy_001.md，policy_041.md，policy_049.md
```

流程判断：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app --query "这个 8000 元采购申请是否需要审批？" --role employee
```

项目分析：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app --query "帮我分析 A 项目当前有哪些风险。" --role manager
```

数据分析：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app --query "统计当前高风险项目" --role manager
```

数据分析会调用：

```text
query_sql + generate_report
```

并输出来自 `business.db` 的 `source/milestone/risks` 字段。

## 9. 验收结果

已验证：

* 制度问答调用 `search_kb`
* 流程判断调用 `search_kb + workflow_check`
* 项目分析调用 `search_kb + generate_report`
* 数据分析调用 `query_sql + generate_report`
* Runtime 输出包含 `answer/task_type/tool_calls`
* CLI 可从项目根目录运行
* M1 原有测试继续通过
* `business.db` 由已有项目文档解析生成

最终测试：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests -q
```

结果：

```text
31 passed in 6.65s
```

## 10. M2 未做内容

以下内容仍按原计划留到 M3/M4：

* 真实 LLM 调用
* 完整 Verifier
* Retry 执行策略
* Trace Logger
* Embedding/vector backend
* 复杂权限系统
* LangGraph checkpoint/persistence
* 多 Agent 或 subgraph 编排

## 11. 下一步建议

M3 可以优先做：

* 为 `Runtime.run()` 和 CLI 暴露 `top_k`
* 为 `query_sql` 增加更多受控 query_type
* 引入 Trace Logger 记录每次工具输入、输出、latency 和错误
* 增加 Verifier，检查答案是否包含来源、是否错误使用无证据结论
* 将 `answer_generator_node` 替换为可选 LLM 生成，但保留当前模板作为 fallback
