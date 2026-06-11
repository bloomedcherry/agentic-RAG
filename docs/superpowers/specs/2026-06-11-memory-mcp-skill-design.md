# Memory、LLM、Skill 与 MCP 集成设计

## 1. 目标

在现有单 Supervisor Agent + LangGraph Runtime 基础上，引入以下能力：

1. OpenAI-compatible LLM Gateway，兼容本地 vLLM 和第三方厂商 API。
2. 同一用户会话内可持久化、可恢复的短期记忆。
3. 配置式 Skill，并使用渐进式披露控制上下文。
4. 自建企业 MCP Server，将 `query_sql` 和 `workflow_check` 作为 MCP 工具暴露。
5. 本地使用 SQLite 完成功能联调，部署时可切换 PostgreSQL。
6. 提供 Docker Compose 配置，但本阶段不要求完成 Docker 环境验收。

本阶段继续保持单 Supervisor Agent，不引入 Multi-Agent。

## 2. 设计原则

- 项目核心接口保持框架无关，LangGraph 继续只承担 Runtime 编排。
- Memory、业务数据库和 Trace 使用独立存储边界。
- Router 和 Permission 不感知工具来自本地实现还是 MCP。
- Skill 定义任务流程，不直接实现底层业务能力。
- 完整消息持久化，但只把摘要和最近消息放入模型上下文。
- 外部模型、Memory 后端或 MCP 服务异常时，保留 M4 规则链路作为降级路径。
- 同一 `user_id + thread_id` 串行执行，不同会话允许并行。

## 3. 总体编排

```text
CLI / Future API
  │
  ├─ user_id
  ├─ thread_id
  └─ query
  ↓
Session Lock
  ↓
Memory Reader
  ├─ 完整消息持久化
  ├─ 历史增量摘要
  └─ 最近 10 轮，受 Token 上限约束
  ↓
Planner
  ├─ Main LLM
  └─ Rule Planner fallback
  ↓
Skill Selector
  ├─ 规则预筛选
  ├─ Utility LLM 最终选择
  └─ 无匹配时进入通用 Router
  ↓
Skill Executor / General Router
  ↓
Tool Registry
  ├─ Local: search_kb
  ├─ Local: generate_report
  ├─ MCP: query_sql
  └─ MCP: workflow_check
  ↓
Context Builder
  ↓
Main LLM Answer Generator
  └─ Template fallback
  ↓
Verifier / Retry / Refusal
  ↓
Memory Writer
  ├─ 保存完整消息
  ├─ 增量更新摘要
  └─ 保存 Checkpoint
  ↓
Trace Logger
```

## 4. 实施顺序

```text
1. 统一配置与 LLM Gateway
2. SQLite/PostgreSQL Memory 抽象
3. 会话恢复、增量摘要、会话管理 CLI
4. Skill Registry / Selector / Executor
5. 企业 MCP Server + Tool Adapter
6. 集成测试
7. Docker Compose 配置
```

每一步都必须保留已有 M1-M4 测试和规则降级链路。

## 5. LLM Gateway

### 5.1 接口

业务模块只依赖统一接口，不直接依赖具体厂商 SDK：

```python
class LLMClient:
    def complete(self, messages, response_schema=None, **options): ...
```

支持：

- 本地 vLLM OpenAI-compatible endpoint。
- OpenAI 或其他兼容 `/v1/chat/completions` 的厂商 API。
- 自动化测试使用的确定性 Fake LLM。

具体 vLLM 模型不写死在项目中，由部署配置决定。

### 5.2 模型职责

主模型与辅助模型独立配置：

- Main LLM：Planner、工具参数生成、最终回答。
- Utility LLM：会话摘要、Skill 选择、轻量结构化提取。

建议配置：

```text
MAIN_LLM_BASE_URL
MAIN_LLM_API_KEY
MAIN_LLM_MODEL
UTILITY_LLM_BASE_URL
UTILITY_LLM_API_KEY
UTILITY_LLM_MODEL
```

### 5.3 降级策略

```text
Main LLM 不可用
→ 尝试备用 OpenAI-compatible endpoint
→ 规则 Planner + 模板回答

Utility LLM 不可用
→ Skill 选择退化为规则选择
→ 摘要延迟生成
→ 最近消息继续可用
```

模型调用需要记录 provider、model、latency、token usage、status 和 error_type，但不能记录 API Key。

## 6. 会话 Memory

### 6.1 范围

本阶段实现同一会话内的短期记忆，程序重启后仍可恢复。暂不实现跨会话用户偏好和长期语义记忆。

隔离键：

```text
user_id + thread_id
```

所有读取、删除和恢复操作都必须同时校验这两个字段。

### 6.2 上下文策略

数据库保存完整原始消息。提供给模型的上下文为：

```text
系统提示
+ 历史增量摘要
+ 最近最多 10 轮原始消息
+ 当前任务状态
+ 当前必要工具结果
```

同时设置 Token 上限。即使未达到 10 轮，只要超过 Token 阈值也提前摘要。

摘要由 Utility LLM 增量更新，结构至少包括：

```json
{
  "user_goal": "",
  "known_facts": [],
  "decisions": [],
  "open_items": [],
  "referents": {}
}
```

原始消息始终保留，摘要是可重建的派生数据。

### 6.3 双后端

本地开发：

```text
MEMORY_BACKEND=sqlite
MEMORY_DATABASE_URL=sqlite:///enterprise_agent/data/memory.db
```

Docker/生产：

```text
MEMORY_BACKEND=postgres
MEMORY_DATABASE_URL=postgresql://...
```

现有 `business.db` 继续作为业务查询数据源，不与 Memory 表混用。

### 6.4 数据模型

至少包含：

- `sessions`：用户、线程、创建时间、更新时间、摘要版本。
- `messages`：角色、内容、时间、消息序号、Token 估算。
- `summaries`：摘要内容、覆盖消息范围、模型、版本。
- `checkpoints`：LangGraph 状态或 Checkpointer 后端数据。

### 6.5 并发

同一 `user_id + thread_id` 使用会话级串行锁：

- SQLite：进程内 keyed lock，适用于本地单进程测试。
- PostgreSQL：事务级 advisory lock 或等价数据库锁。

不同会话不共享锁。

### 6.6 会话管理 CLI

第一版提供：

```text
list
show
delete
```

示例：

```bash
python -m enterprise_agent.memory.cli list --user-id user-001
python -m enterprise_agent.memory.cli show --user-id user-001 --thread-id project-a
python -m enterprise_agent.memory.cli delete --user-id user-001 --thread-id project-a
```

后续生产扩展：

```text
cleanup
export
rebuild-summary
```

## 7. CLI 与会话标识

Agent CLI 增加：

```text
--user-id
--thread-id
```

显式传入时恢复对应会话。未传入时自动生成并输出标识，便于本地继续调用。

生产 API 中 `user_id` 必须来自认证层，不接受客户端任意声明；`thread_id` 必须验证属于当前用户。

## 8. 配置式 Skill

### 8.1 第一版 Skill

- `travel_reimbursement_qa`
- `purchase_approval_check`
- `project_risk_report`

### 8.2 目录

```text
enterprise_agent/skills/
├── registry.py
├── loader.py
├── selector.py
├── executor.py
└── definitions/
    └── project_risk_report/
        ├── SKILL.md
        ├── workflow.yaml
        ├── prompts/
        ├── templates/
        └── references/
```

### 8.3 渐进式披露

第一层，发现：

- `name`
- `description`
- `task_types`
- `keywords`
- `roles`
- `risk_level`

Supervisor 只看到这一层。

第二层，激活：

- 输入 schema
- 执行步骤
- 允许工具
- 输出格式
- Verifier 规则

第三层，执行：

- 当前步骤的 Prompt
- 必要参考文档
- 输出模板
- 少量示例

未执行步骤的资源不进入上下文。

### 8.4 Skill 选择

```text
规则预筛选
→ task_type、role、关键词、权限和风险过滤
→ Utility LLM 对候选元数据做结构化选择
→ 加载选中 Skill
→ 无可靠匹配时进入通用 Planner/Router
```

Skill 选择结果必须包含 `skill_name`、`confidence` 和 `reason`。低于阈值时不激活 Skill。

## 9. MCP

### 9.1 第一版范围

迁移到企业 MCP Server：

- `query_sql`
- `workflow_check`

继续保留为 Runtime 本地工具：

- `search_kb`
- `generate_report`

### 9.2 通信方式

- 本地调试：stdio。
- Docker 部署：Streamable HTTP。

两种方式共用相同 MCP 工具定义，通过配置切换。

### 9.3 Tool Adapter

```text
MCP Tool
→ McpToolAdapter
→ BaseTool
→ ToolRegistry
→ Permission
→ Router / Skill Executor
```

MCP Tool Adapter 负责：

- 将 MCP schema 转换为现有 Tool Contract。
- 统一超时、错误类型和 ToolResult。
- 保留权限、风险等级和 Trace 字段。
- 对服务不可用提供明确错误，不绕过 Permission。

## 10. AgentState 扩展

建议增加：

```python
user_id: str
thread_id: str
messages: list
conversation_summary: dict
summary_version: int
selected_skill: str | None
skill_context: dict
llm_calls: list
memory_status: dict
```

大型工具输出不得无限写入状态，应保存摘要和引用，原始结果按需要存储在工具结果表或 Trace 中。

## 11. 错误处理

新增错误类型：

```text
llm_unavailable
llm_invalid_output
memory_read_error
memory_write_error
summary_error
session_conflict
skill_not_found
skill_invalid
mcp_unavailable
mcp_timeout
mcp_protocol_error
```

基本策略：

- Memory 读取失败：本轮无记忆运行，并明确记录 Trace。
- Memory 写入失败：回答仍可返回，但标记会话未持久化。
- 摘要失败：保留最近消息，不删除未摘要消息。
- Skill 失败：退回通用 Planner/Router。
- MCP 失败：不直接改用绕过权限的本地实现；由配置决定是否允许显式 fallback。
- 结构化 LLM 输出无效：有限次数修复，随后进入规则降级。

## 12. 测试

### 12.1 LLM

- Fake LLM 的确定性结构化输出。
- 主模型失败后规则降级。
- Utility LLM 失败后规则 Skill 选择和延迟摘要。

### 12.2 Memory

- 同一线程第二轮可引用第一轮内容。
- 程序重建 Runtime 后仍恢复会话。
- 最近 10 轮和 Token 阈值同时生效。
- 摘要覆盖范围和版本递增。
- 不同 `user_id` 不能读取相同 `thread_id` 的会话。
- `list/show/delete` CLI。
- 同一线程并发请求串行。

### 12.3 Skill

- 只加载第一层元数据做候选筛选。
- 激活后才读取完整 workflow。
- 执行到步骤时才加载 Prompt/reference。
- LLM 低置信度时回退通用流程。
- 三个内置 Skill 的端到端测试。

### 12.4 MCP

- stdio MCP Server 的工具发现和调用。
- MCP schema 到 BaseTool 的映射。
- Permission 在 MCP 调用前执行。
- 超时、服务不可用和协议错误。
- Streamable HTTP 配置解析测试。

### 12.5 回归

- M1-M4 全量测试继续通过。
- Memory/Skill/MCP 未启用时，现有 CLI 行为保持兼容。
- Eval 增加多轮 Memory、Skill 选择和 MCP 工具任务。

## 13. 本阶段验收

1. OpenAI-compatible 主模型和辅助模型可独立配置。
2. 无模型服务时现有规则和模板链路仍可运行。
3. SQLite 下同一会话可跨进程恢复。
4. Memory 后端可配置切换到 PostgreSQL。
5. 会话管理支持 `list/show/delete`。
6. 三个配置式 Skill 可被渐进式发现、选择和执行。
7. `query_sql`、`workflow_check` 可通过 stdio MCP 调用。
8. 提供 Streamable HTTP 和 Docker Compose 配置。
9. 同一会话串行，不同会话可并行。
10. 新增测试与现有 M1-M4 测试全部通过。

## 14. 非目标

本阶段不实现：

- 跨会话长期语义记忆。
- 用户画像和偏好自动学习。
- 多 Agent 或 Subagent 调度。
- Agentic RL 或自进化。
- 任意 SQL。
- 生产级身份认证平台。
- Docker 环境的正式性能和高可用验收。

