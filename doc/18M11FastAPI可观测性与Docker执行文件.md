# M11 FastAPI、可观测性与 Docker 执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Follow TDD and verify local services before claiming completion.

**Goal:** 将 CLI Runtime 服务化，加入异步 API、健康检查、结构化日志、Metrics、Trace 关联和 Docker Compose 部署配置。

**Architecture:** FastAPI 只负责认证、请求校验和调用 `Runtime.arun()`。PostgreSQL 保存 Memory/Checkpoint，企业 MCP Server 作为独立服务。日志、指标和 Trace 使用统一 request_id/task_id/thread_id 关联。

**Tech Stack:** FastAPI, Uvicorn, Pydantic, OpenTelemetry, Prometheus client, Docker Compose, PostgreSQL。

---

## 1. 文件清单

创建：

```text
enterprise_agent/api/
├── __init__.py
├── app.py
├── dependencies.py
├── schemas.py
├── routes_chat.py
├── routes_sessions.py
├── routes_health.py
└── errors.py
enterprise_agent/observability/
├── logging.py
├── metrics.py
└── tracing.py
enterprise_agent/tests/
├── test_api_chat.py
├── test_api_sessions.py
├── test_api_auth.py
├── test_health.py
├── test_metrics.py
└── test_idempotency.py
Dockerfile
docker-compose.yml
.dockerignore
```

## 2. API

```text
POST /v1/chat
GET  /v1/sessions
GET  /v1/sessions/{thread_id}
DELETE /v1/sessions/{thread_id}
GET  /health/live
GET  /health/ready
GET  /metrics
```

`POST /v1/chat` 输入：

```json
{
  "thread_id": "project-a",
  "query": "第二个风险怎么处理？",
  "request_id": "optional-idempotency-key"
}
```

`user_id/tenant_id` 必须来自认证依赖，不从 body 接受。

## 3. 执行任务

### Task 1：异步 Runtime

- [ ] `Runtime.arun()` 完整覆盖 Memory、LLM、Skill、MCP。
- [ ] 同步 CLI 使用受控同步适配。
- [ ] 测试取消请求时释放锁和 MCP session。

### Task 2：Chat API

- [ ] 测试成功、多轮会话、权限拒绝、模型降级、MCP 错误。
- [ ] 错误响应包含稳定 `error_code` 和 `request_id`，不返回堆栈。

### Task 3：Session API

- [ ] list/show/delete 复用 Memory Service。
- [ ] 只能管理当前认证用户的会话。
- [ ] 删除操作记录审计。

### Task 4：健康检查

- [ ] liveness 只检查进程；
- [ ] readiness 检查 PostgreSQL、Memory migrations、必要 MCP 配置；
- [ ] LLM 可配置为 degraded 而非必然 unhealthy。

### Task 5：并发、幂等和超时

- [ ] 同会话串行；
- [ ] `request_id` 重复请求返回已有结果；
- [ ] 配置全链路 deadline；
- [ ] 超时取消未完成工具调用；
- [ ] 不引入无限自动重试。

### Task 6：结构化日志

- [ ] 每条日志包含：

```text
timestamp
level
request_id
task_id
tenant_id
user_id
thread_id
component
event
latency
error_type
```

- [ ] 密钥、Token、完整敏感内容不得写日志。

### Task 7：Metrics 与 Trace

- [ ] Metrics：

```text
requests_total
request_latency_seconds
llm_calls_total
llm_tokens_total
tool_calls_total
mcp_calls_total
memory_operations_total
verifier_failures_total
```

- [ ] 分阶段 span：

```text
memory
planner
skill
retrieval
tool/mcp
generation
verifier
```

### Task 8：Docker

- [ ] Dockerfile 使用非 root 用户；
- [ ] Compose 服务：

```text
agent-api
postgres
enterprise-mcp
```

- [ ] 使用 healthcheck 和 volume；
- [ ] API Key 仅从环境或 secret 注入；
- [ ] 不把本地 `.env`、数据库、Trace、模型权重打入镜像。

### Task 9：文档

- [ ] README 包含本地启动、API 调用、Compose 配置和故障排查。
- [ ] 本阶段只要求提供并校验 Docker 配置；正式部署性能验收进入后续环境。

## 4. 本地验收

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m uvicorn \
  enterprise_agent.api.app:app --host 127.0.0.1 --port 8080

curl http://127.0.0.1:8080/health/live
curl http://127.0.0.1:8080/health/ready
```

## 5. 验收标准

- API 可完成多轮会话；
- user_id 只来自认证层；
- 同会话请求串行且支持幂等；
- readiness 能反映依赖状态；
- Metrics 和 Trace 可关联 request/task/thread；
- Docker Compose 配置通过解析；
- 镜像配置不包含密钥；
- CLI 保持兼容；
- M1-M10 测试继续通过。

