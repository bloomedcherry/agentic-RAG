# Project Review

## 项目目标

构建一个企业 Agentic RAG 知识助手与可控执行 Harness 系统，支持制度问答、流程判断、项目风险分析、受控 SQL 查询和报告草稿生成。项目重点不是训练模型，而是把知识库、工具、权限、校验、Trace 和 Eval 串成可运行、可观测、可评估的 Agent 执行闭环。

## 架构设计

系统采用单 Supervisor Agent + Harness Runtime。Runtime 基于 LangGraph `StateGraph` 编排固定链路：

```text
Planner -> Router -> Tool Executor -> Context Builder -> Answer Generator -> Verifier/Retry -> Trace
```

核心业务接口保持框架无关，工具通过项目自定义 `BaseTool`、`ToolResult` 和 `ToolRegistry` 注册与调用。

## RAG 子系统

M1 构建了中等规模企业知识库，覆盖制度、流程、项目、会议、合同和报告文档。当前检索使用 TF-IDF baseline，`search_kb` 默认 top_k=5，返回 `source`、`chunk_id`、`content` 和 `score`。

M4 实测 RAG Recall@5 为 0.100，说明当前 baseline 可以支撑链路演示，但精确 source 召回仍是后续优化重点。

## Tool Contract / Registry

工具统一声明 `name`、`description`、`input_schema`、`output_schema`、`permission`、`risk_level`、`timeout` 和 `retry_policy`，并统一返回 `ToolResult(status, output, error, latency, error_type)`。

当前工具包括：

- `search_kb`
- `workflow_check`
- `query_sql`
- `generate_report`

## Harness Runtime

M2 实现 LangGraph Runtime，支持从用户 query 到任务分类、工具路由、工具执行、上下文组装和模板回答生成。`Runtime.run(query, user_role, task_id=None)` 是主要入口，CLI 通过 `python -m enterprise_agent.app` 调用。

## Verifier / Retry

M3 增加规则 Verifier，检查检索为空、缺少引用、SQL 错误、权限拒绝、权限绕过和报告格式错误。Retry 模块将错误类型映射为 `retry_with_citation`、`fallback_insufficient_evidence`、`fallback_without_data_claim`、`refusal` 或 `retry_with_format`。

当前权限拒绝会被明确拒绝输出，并在 verifier 中标记为未通过；这有利于安全审计，但会降低端到端 Task Success 指标。

## Trace Logging

每次 Runtime 执行写入 `enterprise_agent/logs/traces.jsonl`，字段包括 `task_id`、`query`、`user_role`、`task_type`、`plan`、`tool_calls`、`retrieved_docs`、`tool_outputs`、`answer`、`verifier_result`、`success`、`latency` 和 `error_type`。

M4 修复了 eval task id 在 LangGraph state 中丢失的问题，使 trace 可以和 eval set 对齐。

## Eval 结果

本轮 M4 构造 50 条 eval 任务并跑通评估脚本：

| Metric | Value |
| --- | ---: |
| RAG Recall@5 | 0.100 |
| Tool Call Accuracy | 1.000 |
| Tool Success Rate | 0.978 |
| Permission Blocking Accuracy | 1.000 |
| Task Success Rate | 0.960 |
| Citation Accuracy | 1.000 |
| Verifier Pass Rate | 0.960 |
| Average Latency | 0.624527s |

## 失败案例

- `task_041`: 普通员工查询所有部门采购金额统计，被 `query_sql` 权限拦截。
- `task_042`: 普通员工查询高风险项目列表，被 `query_sql` 权限拦截。

这两条在安全意义上符合预期，但当前 Task Success 定义要求 `verifier_result.pass == true`，因此被计为失败。

## 后续扩展

- 引入更强检索方案，例如 BM25 + embedding hybrid retrieval 或 rerank。
- 将权限拒绝类任务拆分为安全成功指标，避免和普通任务成功率混淆。
- 增加受控 SQL query_type，例如部门采购金额聚合。
- 增加 LLM-as-Judge 评估引用一致性和答案覆盖率。
- 增加 trace 清理或按 run_id 分组，便于复现实验批次。

