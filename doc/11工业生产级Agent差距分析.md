# 工业生产级 Agent 差距分析

## 1. 当前完成度

当前系统已经完成 Agent Harness Demo 的主要闭环：

```text
RAG
+ Tool Contract / Registry
+ LangGraph Runtime
+ Planner / Router
+ Permission
+ Verifier / Retry / Refusal
+ Trace Logging
+ Eval
```

粗略评估：

- 功能原型完成度：约 40%。
- 生产工程完成度：约 20%。
- 距离可稳定上线的工业生产级 Agent：仍缺约 70% 的工程能力。

这里的比例用于描述工程阶段，不代表正式量化评测结果。

## 2. 缺失能力优先级

### P0：上线前必须完成

#### 2.1 真实 LLM 执行层

当前回答以规则和模板为主。仍需：

- OpenAI-compatible LLM Gateway。
- 主模型与辅助模型独立配置。
- 结构化输出校验和修复。
- 超时、重试、备用模型和规则降级。
- Token、成本、延迟和错误统计。
- Prompt 版本管理。

#### 2.2 高质量 RAG

当前使用 TF-IDF baseline，M4 实测 RAG Recall@5 为 0.100。仍需：

- BM25 与向量混合检索。
- Embedding 模型。
- Metadata Filter。
- Reranker。
- Query Rewrite。
- 增量索引和索引版本管理。
- 引用是否支持结论的校验。

#### 2.3 数据权限与安全

当前主要是角色级工具权限。仍需：

- 身份认证。
- Tenant、用户和部门隔离。
- 行级和字段级数据权限。
- 敏感字段脱敏。
- 高风险操作确认和 HITL。
- Prompt Injection 和工具注入防护。
- 审计、数据保留和删除策略。

#### 2.4 服务化与可靠性

当前以 CLI 为主。仍需：

- FastAPI 或等价服务接口。
- 异步执行和并发控制。
- 超时、熔断、重试和幂等。
- 数据库连接池和缓存。
- 配置、密钥和环境管理。
- 容器部署、健康检查和滚动发布。

#### 2.5 生产评测与质量门禁

当前有 50 条 Demo Eval Set。仍需：

- 人工校验的 Gold Set。
- 更大规模的业务测试集。
- 安全攻击和越权测试集。
- Baseline 与消融实验。
- P95/P99 延迟与成本指标。
- CI 自动回归和发布门禁。
- 线上反馈和失败样本回流。

### P1：稳定性和体验的重要能力

#### 2.6 Memory

仍需：

- 完整消息持久化。
- `user_id + thread_id` 会话隔离。
- Checkpoint 和程序重启恢复。
- 最近消息与历史摘要组合。
- Token 阈值触发的增量摘要。
- 会话管理、并发控制和数据删除。

#### 2.7 动态 Planner

当前主要为规则分类。仍需：

- LLM 任务识别。
- 多步骤计划。
- 工具参数生成。
- 计划修正和停止条件。
- 结构化 Planner 输出。
- 规则和模型双重降级。

#### 2.8 真正的 Retry 与自纠错

当前以简单 fallback 为主。仍需：

- 检索失败后 Query Rewrite。
- 工具失败后参数修复。
- 无效结构化输出重生成。
- Verifier 失败后定向重试。
- 最大步骤和最大成本约束。

#### 2.9 工具体系和 MCP

当前工具数量有限，SQL query type 固定。仍需：

- 更多受控业务工具。
- MCP Client 和企业 MCP Server。
- 工具发现和 schema 适配。
- 工具级超时、重试和熔断。
- MCP 服务认证和网络安全。
- 工具版本与兼容性治理。

#### 2.10 Skill

仍需：

- Skill Registry。
- 规则预筛选和 LLM 选择。
- 渐进式披露。
- Skill 版本、权限和风险信息。
- 通用执行器和输出校验。
- Skill 测试和评估指标。

#### 2.11 可观测性

当前使用本地 JSONL Trace。仍需：

- 结构化日志和统一 Trace ID。
- Metrics、Dashboard 和 Alert。
- LLM、Memory、Skill、MCP 分阶段耗时。
- 错误聚合和根因分析。
- OpenTelemetry 或等价标准接入。

### P2：按业务需要扩展

#### 2.12 HITL

高风险写操作、敏感数据访问和外部系统变更需要人工确认、审批超时和恢复机制。

#### 2.13 Multi-Agent

当前单 Supervisor 足以支撑主要场景。只有任务边界、上下文隔离或团队职责明确时，才考虑 Research、SQL、Report、Verifier 等 Subagent。

#### 2.14 Agentic RL 和自进化

不属于当前上线前提。需要在稳定 Trace、可信 Eval、充足反馈数据和安全回滚机制建立后再考虑。

## 3. 推荐建设顺序

```text
第一阶段
统一配置 + LLM Gateway

第二阶段
会话 Memory + Checkpoint + 摘要

第三阶段
配置式 Skill + 渐进式披露

第四阶段
企业 MCP Server + Tool Adapter

第五阶段
Hybrid RAG + Rerank

第六阶段
身份、细粒度权限和安全防护

第七阶段
FastAPI 服务化 + 可观测性 + Docker 部署

第八阶段
Gold Set + CI 质量门禁 + 正式消融实验
```

对应分步执行文件：

| 里程碑 | 执行文件 | 核心交付 |
| --- | --- | --- |
| M5 | `doc/12M5统一配置与LLMGateway执行文件.md` | OpenAI-compatible 主/辅助模型、结构化输出、规则降级 |
| M6 | `doc/13M6会话Memory与Checkpoint执行文件.md` | SQLite/PostgreSQL Memory、Checkpoint、摘要、会话管理 |
| M7 | `doc/14M7配置式Skill与渐进式披露执行文件.md` | Skill Registry、选择、执行、渐进式加载 |
| M8 | `doc/15M8企业MCP工具与双传输执行文件.md` | 企业 MCP Server、stdio、Streamable HTTP、Tool Adapter |
| M9 | `doc/16M9HybridRAG与Rerank执行文件.md` | BM25、Embedding、Hybrid、Rerank、Query Rewrite |
| M10 | `doc/17M10身份细粒度权限与安全控制执行文件.md` | 身份、数据范围、脱敏、注入防护、HITL |
| M11 | `doc/18M11FastAPI可观测性与Docker执行文件.md` | API、异步 Runtime、日志指标、Docker Compose |
| M12 | `doc/19M12生产评测质量门禁与项目收口执行文件.md` | Gold Set、生产指标、CI 门禁、项目收口 |

## 4. 当前下一阶段范围

下一阶段已确定实现：

- OpenAI-compatible 主模型与辅助模型。
- SQLite 本地、PostgreSQL 部署的 Memory 双后端。
- 同一会话持久化、最近 10 轮与 Token 上限、增量摘要。
- `list/show/delete` 会话管理。
- 三个配置式 Skill：
  - `travel_reimbursement_qa`
  - `purchase_approval_check`
  - `project_risk_report`
- 规则预筛选、LLM 选择和渐进式披露。
- 自建企业 MCP Server。
- `query_sql` 和 `workflow_check` MCP 化。
- stdio 本地通信和 Streamable HTTP 部署配置。
- 模型、Memory、Skill、MCP 失败时回退现有 M4 规则链路。

该阶段完成后，系统会从可评估 Harness Demo 进一步升级为具备真实模型、多轮会话记忆、可复用任务流程和标准化外部工具协议的 Agent 系统，但仍不等同于完成生产级安全、服务高可用和正式质量门禁。
