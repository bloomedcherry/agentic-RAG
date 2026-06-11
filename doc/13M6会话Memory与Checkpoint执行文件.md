# M6 会话 Memory、Checkpoint 与摘要执行文件

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

- [ ] 写 `test_config.py` 失败测试：
  - 默认 `MEMORY_BACKEND=sqlite`；
  - 默认路径是 `enterprise_agent/data/memory.db`；
  - PostgreSQL 缺 URL 时配置校验失败；
  - `MEMORY_MAX_RECENT_TURNS=10`；
  - Token 阈值可配置。
- [ ] 更新 `environment.yml`、`config.py`、`.env.example`。
- [ ] `.gitignore` 忽略本地 `memory.db`、WAL 和 SHM 文件。

### Task 2：SQLite MemoryStore

- [ ] 在 `test_memory_sqlite.py` 写失败测试：
  - 创建会话；
  - 追加 user/assistant 消息；
  - 按序读取；
  - 保存和更新摘要版本；
  - 不同用户相同 thread 隔离；
  - 删除会话级联删除消息和摘要。
- [ ] 实现迁移函数，创建：

```text
sessions(user_id, thread_id, created_at, updated_at, summary_version)
messages(id, user_id, thread_id, seq, role, content, token_count, created_at)
summaries(id, user_id, thread_id, version, covered_until_seq, content_json, model, created_at)
```

- [ ] 联合唯一键必须包含 `user_id, thread_id`。

### Task 3：PostgreSQL MemoryStore

- [ ] 使用接口契约测试，SQLite 与 PostgreSQL 共享测试用例。
- [ ] PostgreSQL 集成测试通过环境变量启用；未提供数据库时标记 skip，不伪造通过。
- [ ] 使用参数化 SQL/SQLAlchemy，禁止字符串拼接用户输入。

### Task 4：LangGraph Checkpointer Factory

- [ ] 写失败测试：SQLite 配置返回 `SqliteSaver`，PostgreSQL 配置返回 `PostgresSaver`。
- [ ] `build_graph()` 接收 `checkpointer` 并调用：

```python
graph.compile(checkpointer=checkpointer)
```

- [ ] Runtime 调用图时传入内部安全 thread key：

```python
checkpoint_thread_id = sha256(f"{user_id}:{thread_id}".encode()).hexdigest()
config = {"configurable": {"thread_id": checkpoint_thread_id}}
```

- [ ] 禁止只用客户端 `thread_id` 作为跨用户主键。

### Task 5：上下文窗口与增量摘要

- [ ] 在 `test_memory_context.py` 写失败测试：
  - 不超过阈值时保留最近消息；
  - 超过 10 轮时旧消息进入摘要范围；
  - 未满 10 轮但超 Token 阈值时提前摘要；
  - 摘要失败时不删除消息；
  - 新摘要基于旧摘要增量更新；
  - `referents` 能保存“第二个风险”对应实体。
- [ ] `MemoryManager.load_context()` 返回：

```python
{
    "summary": {...},
    "recent_messages": [...],
    "total_tokens": 0,
    "needs_summary": False
}
```

- [ ] Token 计算优先使用模型 usage/tokenizer；不可用时使用确定性估算并标记 `estimated=true`。

### Task 6：Runtime 会话编排

- [ ] 在 `test_memory_runtime.py` 写失败测试：
  - 第一轮分析 A 项目；
  - 第二轮询问“第二个风险”；
  - 重建 Runtime 后继续同一会话；
  - 新 thread 不继承旧会话；
  - 不同 user 不共享会话；
  - Memory 写入失败时回答仍返回并记录 `memory_write_error`。
- [ ] Graph 增加：

```text
memory_reader_node
...
memory_writer_node
```

- [ ] `ContextBuilder` 拼接摘要和最近消息，但不拼接完整历史。

### Task 7：会话串行锁

- [ ] 在 `test_session_lock.py` 写并发测试：同一会话不可重叠执行，不同会话可以并行。
- [ ] SQLite 使用进程内 keyed lock。
- [ ] PostgreSQL 使用 advisory lock 或等价事务锁；锁必须有超时和 `session_conflict` 错误。

### Task 8：会话管理 CLI

- [ ] 在 `test_memory_cli.py` 写失败测试覆盖：

```text
list --user-id
show --user-id --thread-id
delete --user-id --thread-id
```

- [ ] `show` 输出消息数量、摘要版本、更新时间和最近消息；默认不输出完整敏感工具结果。
- [ ] `delete` 需要 `--yes` 或交互确认。

### Task 9：Agent CLI

- [ ] `enterprise_agent.app` 增加：

```text
--user-id
--thread-id
```

- [ ] 未传时生成标识并输出；显式传入时恢复会话。
- [ ] API 设计说明明确：生产 user_id 必须来自认证层。

## 6. 本地调用

```bash
MEMORY_BACKEND=sqlite \
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "帮我分析 A 项目风险" \
  --role manager \
  --user-id user-001 \
  --thread-id project-a

MEMORY_BACKEND=sqlite \
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "第二个风险怎么处理？" \
  --role manager \
  --user-id user-001 \
  --thread-id project-a
```

## 7. 验收标准

- 第二轮能够读取第一轮上下文；
- Runtime 重建后会话仍可恢复；
- 完整消息已持久化，但模型只接收摘要和最近窗口；
- 不同用户无法读取同名 thread；
- 摘要失败不导致消息丢失；
- `list/show/delete` 可运行；
- SQLite 本地测试通过；
- PostgreSQL 后端接口和可选集成测试具备；
- M1-M5 全量测试继续通过。

## 8. 官方参考

- LangGraph Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph Memory: https://docs.langchain.com/oss/python/langgraph/add-memory
- SQLite Checkpointer: `langgraph-checkpoint-sqlite`
- PostgreSQL Checkpointer: `langgraph-checkpoint-postgres`
