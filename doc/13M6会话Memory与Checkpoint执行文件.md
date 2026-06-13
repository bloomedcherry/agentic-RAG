# M6 会话 Memory、Checkpoint 与摘要执行文件

**执行状态：已完成并通过回归验证（更新于 2026-06-13）**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Follow TDD and preserve M1-M5 behavior.

**Goal:** 实现按 `user_id + thread_id` 隔离、程序重启后可恢复的会话记忆，采用完整消息持久化、最近 10 轮和 Token 上限、增量摘要的工业式短期 Memory。

**Architecture:** 项目自定义 `MemoryStore` 管理 sessions/messages/summaries，LangGraph Checkpointer 管理图状态。SQLite 用于本地联调，PostgreSQL 用于部署；业务数据库 `business.db` 保持独立。

**Tech Stack:** Python, sqlite3/SQLAlchemy, LangGraph SqliteSaver/PostgresSaver, PostgreSQL, pytest。

---

## 1. 前置条件

- M5 已完成；
- 安装官方 Checkpointer：

```text
langgraph-checkpoint-sqlite
langgraph-checkpoint-postgres
psycopg[binary,pool]
```

如需安装，使用项目约定的 `27890` 代理和镜像源。

## 2. 阶段边界

必须完成：

- SQLite/PostgreSQL 双 Memory 后端；
- `user_id + thread_id` 隔离；
- 完整消息、会话摘要和 Checkpoint；
- 最近最多 10 轮，同时受 Token 上限约束；
- Utility LLM 增量摘要，失败时保留最近消息；
- 同一会话串行锁；
- `list/show/delete` 会话管理 CLI；
- CLI 自动或显式生成会话标识。

本阶段不做：

- 跨会话长期语义记忆；
- 用户画像；
- 向量化 Memory；
- Web 会话管理界面。

## 3. 文件清单

创建：

```text
enterprise_agent/memory/
├── __init__.py
├── base.py
├── models.py
├── sqlite_store.py
├── postgres_store.py
├── checkpointer.py
├── manager.py
├── summarizer.py
├── locks.py
└── cli.py
enterprise_agent/tests/
├── test_memory_sqlite.py
├── test_memory_context.py
├── test_memory_runtime.py
├── test_memory_cli.py
└── test_session_lock.py
```

修改：

```text
environment.yml
enterprise_agent/config.py
enterprise_agent/agent/state.py
enterprise_agent/agent/graph.py
enterprise_agent/agent/runtime.py
enterprise_agent/agent/context_builder.py
enterprise_agent/app.py
.gitignore
.env.example
README.md
```

## 4. 核心接口

```python
class MemoryStore(Protocol):
    def create_or_touch_session(self, user_id: str, thread_id: str) -> Session: ...
    def append_message(self, user_id: str, thread_id: str, message: Message) -> None: ...
    def list_messages(self, user_id: str, thread_id: str) -> list[Message]: ...
    def get_summary(self, user_id: str, thread_id: str) -> Summary | None: ...
    def save_summary(self, user_id: str, thread_id: str, summary: Summary) -> None: ...
    def list_sessions(self, user_id: str) -> list[Session]: ...
    def delete_session(self, user_id: str, thread_id: str) -> None: ...
```

## 5. 执行任务

### Task 1：依赖与 Memory 配置

- [x] 写 `test_config.py` 失败测试：
  - 默认 `MEMORY_BACKEND=sqlite`；
  - 默认路径是 `enterprise_agent/data/memory.db`；
  - PostgreSQL 缺 URL 时配置校验失败；
  - `MEMORY_MAX_RECENT_TURNS=10`；
  - Token 阈值可配置。
- [x] 更新 `environment.yml`、`config.py`、`.env.example`。
- [x] `.gitignore` 忽略本地 `memory.db`、WAL 和 SHM 文件。

### Task 2：SQLite MemoryStore

- [x] 在 `test_memory_sqlite.py` 写失败测试：
  - 创建会话；
  - 追加 user/assistant 消息；
  - 按序读取；
  - 保存和更新摘要版本；
  - 不同用户相同 thread 隔离；
  - 删除会话级联删除消息和摘要。
- [x] 实现迁移函数，创建：

```text
sessions(user_id, thread_id, created_at, updated_at, summary_version)
messages(id, user_id, thread_id, seq, role, content, token_count, created_at)
summaries(id, user_id, thread_id, version, covered_until_seq, content_json, model, created_at)
```

- [x] 联合唯一键必须包含 `user_id, thread_id`。

### Task 3：PostgreSQL MemoryStore

- [x] 使用统一 `MemoryStore` 契约实现 SQLite 与 PostgreSQL 后端。
- [x] PostgreSQL 集成测试通过环境变量启用；未提供数据库时标记 skip，不伪造通过。
- [x] 使用参数化 SQL，禁止字符串拼接用户输入。

### Task 4：LangGraph Checkpointer Factory

- [x] 写失败测试：SQLite 配置返回 `SqliteSaver`，PostgreSQL 配置返回 `PostgresSaver`。
- [x] `build_graph()` 接收 `checkpointer` 并调用：

```python
graph.compile(checkpointer=checkpointer)
```

- [x] Runtime 调用图时传入内部安全 thread key：

```python
checkpoint_thread_id = sha256(f"{user_id}:{thread_id}".encode()).hexdigest()
config = {"configurable": {"thread_id": checkpoint_thread_id}}
```

- [x] 禁止只用客户端 `thread_id` 作为跨用户主键。

### Task 5：上下文窗口与增量摘要

- [x] 在 `test_memory_context.py` 写失败测试：
  - 不超过阈值时保留最近消息；
  - 超过 10 轮时旧消息进入摘要范围；
  - 未满 10 轮但超 Token 阈值时提前摘要；
  - 摘要失败时不删除消息；
  - 新摘要基于旧摘要增量更新；
  - `referents` 能保存“第二个风险”对应实体。
- [x] `MemoryManager.load_context()` 返回：

```python
{
    "summary": {...},
    "recent_messages": [...],
    "total_tokens": 0,
    "needs_summary": False
}
```

- [x] Token 不可直接归因到单条消息时使用确定性估算并标记 `estimated=true`。

### Task 6：Runtime 会话编排

- [x] 在 `test_memory_runtime.py` 写失败测试：
  - 第一轮分析 A 项目；
  - 第二轮询问“第二个风险”；
  - 重建 Runtime 后继续同一会话；
  - 新 thread 不继承旧会话；
  - 不同 user 不共享会话；
  - Memory 写入失败时回答仍返回并记录 `memory_write_error`。
- [x] Graph 增加：

```text
memory_reader_node
...
memory_writer_node
```

- [x] `ContextBuilder` 拼接摘要和最近消息，但不拼接完整历史。

### Task 7：会话串行锁

- [x] 在 `test_session_lock.py` 写并发测试：同一会话不可重叠执行，不同会话可以并行。
- [x] SQLite 使用进程内 keyed lock。
- [x] PostgreSQL 使用 advisory lock；锁有超时和 `session_conflict` 错误。

### Task 8：会话管理 CLI

- [x] 在 `test_memory_cli.py` 写失败测试覆盖：

```text
list --user-id
show --user-id --thread-id
delete --user-id --thread-id
```

- [x] `show` 输出消息数量、摘要版本、更新时间和最近消息；默认不输出完整敏感工具结果。
- [x] `delete` 需要 `--yes`，并同步删除对应 Checkpoint。

### Task 9：Agent CLI

- [x] `enterprise_agent.app` 增加：

```text
--user-id
--thread-id
```

- [x] 未传时生成标识并输出；显式传入时恢复会话。
- [x] API 设计说明明确：生产 user_id 必须来自认证层。

## 6. 本地调用

### 6.1 同一会话多轮调用

每一轮都使用相同的 `user_id + thread_id`。CLI 每次启动一个新进程，
但 Memory 和 Checkpoint 会从数据库恢复，因此仍属于同一个多轮会话。

```bash
MEMORY_BACKEND=sqlite \
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "帮我分析 A 项目风险" \
  --role manager \
  --user-id user-001 \
  --thread-id project-a \
  --llm-enabled

MEMORY_BACKEND=sqlite \
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "第二个风险怎么处理？" \
  --role manager \
  --user-id user-001 \
  --thread-id project-a \
  --llm-enabled
```

### 6.2 多会话管理

同一用户更换 `thread_id` 即可创建独立会话，不同 `user_id` 之间也相互隔离：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "差旅报销需要哪些材料？" \
  --role employee \
  --user-id user-001 \
  --thread-id travel-expense \
  --llm-enabled
```

查看和删除会话：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python \
  -m enterprise_agent.memory.cli list \
  --user-id user-001

/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python \
  -m enterprise_agent.memory.cli show \
  --user-id user-001 \
  --thread-id project-a

/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python \
  -m enterprise_agent.memory.cli delete \
  --user-id user-001 \
  --thread-id project-a \
  --yes
```

## 7. 验收标准

- [x] 第二轮能够读取第一轮上下文；
- [x] Runtime 重建后会话仍可恢复；
- [x] 完整消息已持久化，但模型只接收摘要和最近窗口；
- [x] 同一用户可以管理多个相互隔离的 thread；
- [x] 不同用户无法读取同名 thread；
- [x] 摘要失败不导致消息丢失；
- [x] `list/show/delete` 可运行，删除需要显式传入 `--yes`；
- [x] SQLite 本地测试通过；
- [x] PostgreSQL 后端接口和可选集成测试具备；
- [x] M1-M5 全量测试继续通过。

## 8. 官方参考

- LangGraph Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph Memory: https://docs.langchain.com/oss/python/langgraph/add-memory
- SQLite Checkpointer: `langgraph-checkpoint-sqlite`
- PostgreSQL Checkpointer: `langgraph-checkpoint-postgres`

## 9. 实际验证结果

- SQLite Memory、摘要窗口、Checkpoint、会话隔离、Runtime 重建恢复和 CLI 已自动化验证。
- PostgreSQL Store、PostgresSaver 工厂和 advisory lock 已实现；真实 PostgreSQL 契约测试通过 `TEST_MEMORY_POSTGRES_URL` 开启，当前无测试库时明确 skip。
- 同一用户可以通过不同 `thread_id` 管理多个会话；同一 `user_id + thread_id` 可跨 CLI 进程连续多轮回答。
- 本地双轮 CLI 和真实 MiMo API 联调均确认会话可恢复，追问能够读取上一轮问题、回答及来源文件。
- 修正 OpenAI 兼容 SDK 的隐藏重试：SDK 设置 `max_retries=0`，统一由项目 LLM Gateway 控制重试次数，避免超时叠加造成 CLI 长时间无输出。
- 增加主模型上下文窗口、输出 Token 和 Agent 上下文字符预算配置；MiMo 本地配置可使用 1M 上下文窗口，但实际注入仍受 Memory Token 窗口和 Agent 字符预算约束。
- Verifier 可以识别会话历史回答中的显式来源文件，例如 `report_008.md`，不会因为本轮检索结果不同而追加无关来源。
- 最新全量自动化测试结果见下方“最终验证记录”；未配置 `TEST_MEMORY_POSTGRES_URL` 时，真实 PostgreSQL 集成测试明确标记 skip。
- 未执行任何 Git commit、reset 或 push；版本提交由用户处理。

## 10. 实际运行链路

```text
CLI / Runtime.run()
→ 解析或生成 user_id + thread_id
→ 获取同一会话串行锁
→ 使用安全哈希 thread key 加载 LangGraph Checkpoint
→ memory_reader_node 读取摘要和最近消息
→ Planner / Router / Tool Executor
→ Context Builder 注入会话上下文和本轮证据
→ Answer Generator
→ memory_writer_node 持久化本轮 user/assistant 消息
→ Verifier / Trace
→ CLI 输出
```

Memory 数据库保存完整会话消息；发送给模型的不是无限完整历史，而是：

```text
增量摘要 + 最近最多 10 轮 + Token 上限裁剪
```

这使本地 SQLite 联调和后续 PostgreSQL/Docker 部署使用同一套接口。

## 11. 与原计划的实现差异

1. Memory 与业务数据库保持物理分离。默认本地 Memory 使用
   `enterprise_agent/data/memory.db`，业务查询继续使用 `business.db`。
2. CLI 当前是“一次命令一轮回答”，通过持久化数据库实现跨进程多轮；
   M6 不包含持续打开的终端 REPL、Web API 或前端聊天框。
3. PostgreSQL 实现和测试入口已具备，但默认开发验证使用 SQLite；
   只有设置 `TEST_MEMORY_POSTGRES_URL` 才执行真实 PostgreSQL 集成测试。
4. MiMo 的 1M 上下文配置代表模型能力上限，不表示每轮都发送 1M Token。
   系统继续使用渐进式披露，只注入与当前回答相关的摘要、最近消息和证据。

## 12. 已知边界与后续阶段

- M6 提供的是单会话短期记忆，不包括跨 thread 的用户长期语义记忆。
- 尚未实现用户画像、向量化 Memory、跨会话事实检索和记忆重要度/过期策略。
- 尚未实现 FastAPI、SSE 流式输出和前端会话管理页面，这些属于后续服务化阶段。
- 当前图内 `memory_writer_node` 在 Runtime 的图外 Verifier 之前写入回答；
  如果 Verifier 后续替换了答案，Memory 中保存的是验证前版本。生产化时应将
  最终答案写入移动到验证完成之后，或把 Verifier 纳入图内。

## 13. 最终验证记录

执行：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python \
  -m pytest enterprise_agent/tests -q
```

验证结果应以每次执行后的最新输出为准。当前文档更新完成后重新执行全量测试，
结果为：

```text
92 passed, 1 skipped in 52.99s
```

其中 `1 skipped` 是未配置 `TEST_MEMORY_POSTGRES_URL` 时跳过的真实 PostgreSQL
集成测试，不影响 SQLite 默认链路和 PostgreSQL 后端代码的单元测试。
