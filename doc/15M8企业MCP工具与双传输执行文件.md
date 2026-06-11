# M8 企业 MCP 工具与双传输执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Follow TDD.

**Goal:** 自建企业 MCP Server，将 `query_sql` 和 `workflow_check` 通过 MCP 暴露，并使用适配器接回现有 Tool Registry。

**Architecture:** 抽取业务服务层供本地工具和 MCP Server 复用。MCP Client 将远端工具 schema 转换为项目 `BaseTool`；Router、Skill、Permission 和 Verifier 不感知工具来源。本地使用 stdio，Docker 使用 Streamable HTTP。

**Tech Stack:** Official MCP Python SDK (`mcp[cli]`), FastMCP, stdio, Streamable HTTP, pytest。

---

## 1. 前置条件

- M7 完成；
- 安装官方 MCP Python SDK；
- Streamable HTTP 使用无状态 JSON 模式；
- SSE 不作为新实现目标。

## 2. 阶段边界

MCP 化：

```text
query_sql
workflow_check
```

保留本地：

```text
search_kb
generate_report
```

## 3. 文件清单

创建：

```text
enterprise_agent/services/
├── business_query.py
└── workflow_rules.py
enterprise_agent/mcp_server/
├── __init__.py
├── server.py
├── tools.py
└── cli.py
enterprise_agent/mcp_client/
├── __init__.py
├── base.py
├── stdio.py
├── streamable_http.py
├── adapter.py
└── factory.py
enterprise_agent/tests/
├── test_mcp_server.py
├── test_mcp_stdio.py
├── test_mcp_adapter.py
├── test_mcp_permission.py
└── test_mcp_runtime.py
```

修改：

```text
environment.yml
enterprise_agent/config.py
enterprise_agent/tools/base.py
enterprise_agent/tools/runtime_tools.py
enterprise_agent/agent/runtime.py
enterprise_agent/agent/state.py
enterprise_agent/agent/trace.py
.env.example
README.md
```

## 4. 执行任务

### Task 1：抽取业务服务层

- [ ] 为现有 SQL 和流程规则行为写回归测试。
- [ ] 将实际查询逻辑提取为：

```python
BusinessQueryService.execute(query_type, params)
WorkflowRuleService.check(workflow_type, amount)
```

- [ ] 本地 `QuerySqlTool`、`WorkflowCheckTool` 改为调用服务层，行为不变。

### Task 2：FastMCP Server

- [ ] 写失败测试：Server 能列出两个工具及其输入 schema。
- [ ] 使用 `FastMCP` 定义：

```text
query_sql(query_type, params)
workflow_check(workflow_type, amount)
```

- [ ] Server 返回结构化 JSON；错误返回稳定错误码，不泄露数据库路径或堆栈。
- [ ] stdio 模式：

```bash
python -m enterprise_agent.mcp_server.cli --transport stdio
```

- [ ] HTTP 模式：

```bash
python -m enterprise_agent.mcp_server.cli --transport streamable-http --host 0.0.0.0 --port 9000
```

### Task 3：MCP Client 与工具发现

- [ ] stdio 测试启动子进程并执行 MCP initialization、list_tools、call_tool。
- [ ] Streamable HTTP client 使用配置 URL `/mcp`。
- [ ] Client 负责生命周期、超时和关闭；不得每次调用遗留子进程。

### Task 4：McpToolAdapter

- [ ] 写失败测试：
  - MCP metadata 映射为 `BaseTool.metadata()`；
  - 调用结果映射为 `ToolResult`；
  - 超时映射 `mcp_timeout`；
  - 服务不可用映射 `mcp_unavailable`；
  - 协议错误映射 `mcp_protocol_error`。
- [ ] Adapter 保留：

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

### Task 5：异步工具基础

- [ ] 为 `BaseTool` 增加 `async arun/aexecute`，同步工具提供默认适配。
- [ ] Runtime 增加 `arun()`；原 `run()` 作为无事件循环场景的同步包装。
- [ ] FastAPI 阶段将只调用 `arun()`。
- [ ] 测试禁止在已有事件循环中嵌套 `asyncio.run()`。

### Task 6：Permission 与 Registry 集成

- [ ] MCP 工具注册进现有 `ToolRegistry`。
- [ ] Permission 必须在网络调用前执行。
- [ ] employee 调用 MCP `query_sql` 时：

```text
permission_denied
MCP request count = 0
```

- [ ] Router 和 Skill 不包含 MCP transport 分支。

### Task 7：本地与 MCP 切换

- [ ] 配置：

```text
BUSINESS_TOOL_BACKEND=local|mcp
MCP_TRANSPORT=stdio|streamable-http
MCP_SERVER_COMMAND
MCP_SERVER_URL
MCP_TIMEOUT_SECONDS
```

- [ ] MCP 失败时默认不静默调用本地业务工具；只有显式 `MCP_ALLOW_LOCAL_FALLBACK=true` 才允许，并记录 Trace。

### Task 8：Trace 与 Eval

- [ ] Trace 增加：

```text
tool_backend
mcp_transport
mcp_server
mcp_request_id
mcp_fallback_used
```

- [ ] Eval 增加 MCP Tool Success Rate 和 MCP Latency。

## 5. 验收命令

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest \
  enterprise_agent/tests/test_mcp_server.py \
  enterprise_agent/tests/test_mcp_stdio.py \
  enterprise_agent/tests/test_mcp_adapter.py \
  enterprise_agent/tests/test_mcp_permission.py \
  enterprise_agent/tests/test_mcp_runtime.py -q

BUSINESS_TOOL_BACKEND=mcp MCP_TRANSPORT=stdio \
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "这个 8000 元采购申请是否需要审批？" \
  --role employee
```

## 6. 验收标准

- stdio 下两个 MCP 工具可发现、可调用；
- Streamable HTTP Server 配置可启动；
- 工具 schema 正确适配 Tool Contract；
- Permission 在 MCP 网络调用前拦截；
- MCP 错误结构化写入 Trace；
- 本地/MCP 切换不改变 Router 和 Skill；
- M1-M7 全量测试继续通过。

## 7. 官方参考

- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Build an MCP Server: https://modelcontextprotocol.io/docs/develop/build-server
- 生产传输使用 Streamable HTTP；SSE 不作为新实现目标。
