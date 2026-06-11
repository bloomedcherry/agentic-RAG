# M5 统一配置与 LLM Gateway 执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. All behavior changes follow TDD.

**Goal:** 接入真实 OpenAI-compatible 主模型和辅助模型，同时保留现有规则 Planner 与模板回答作为稳定降级路径。

**Architecture:** 新增独立 `llm` 包和统一配置层。Planner、Skill Selector、摘要器和答案生成器只依赖项目自己的 `LLMClient`，不直接依赖 OpenAI、vLLM 或具体厂商 SDK。模型不可用或结构化输出无效时，Runtime 回退 M4 规则链路。

**Tech Stack:** Python 3.10, pydantic-settings, openai Python SDK, pytest。

**执行状态：已完成。** 当前代码保持为未提交工作区修改，Git 提交由用户统一操作。

---

## 1. 阶段边界

必须完成：

- 主模型与辅助模型独立配置；
- 支持本地 vLLM 和第三方 OpenAI-compatible API；
- 支持确定性 Fake LLM；
- LLM Planner 结构化输出；
- LLM Answer Generator；
- 超时、有限重试、备用 endpoint、规则降级；
- Trace 记录模型、延迟、Token、状态和错误；
- 模型名称完全配置化，不在代码中写死。

本阶段不做：

- Memory；
- Skill；
- MCP；
- 流式输出；
- Multi-Agent；
- Prompt 管理平台。

## 2. 文件清单

创建：

```text
enterprise_agent/
├── config.py
├── llm/
│   ├── __init__.py
│   ├── base.py
│   ├── client.py
│   ├── fake.py
│   ├── schemas.py
│   └── prompts.py
└── tests/
    ├── test_config.py
    ├── test_llm_client.py
    ├── test_llm_planner.py
    └── test_llm_runtime.py
.env.example
```

修改：

```text
enterprise_agent/agent/planner.py
enterprise_agent/agent/graph.py
enterprise_agent/agent/runtime.py
enterprise_agent/agent/state.py
enterprise_agent/agent/trace.py
enterprise_agent/app.py
README.md
```

## 3. 数据结构

```python
@dataclass
class LLMRequest:
    messages: list[dict[str, str]]
    response_schema: dict | None = None
    temperature: float = 0.0
    max_tokens: int = 1024


@dataclass
class LLMResponse:
    content: str
    parsed: dict | None
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency: float
    status: str
    error_type: str | None = None
```

Planner 输出：

```json
{
  "task_type": "policy_qa",
  "plan": ["检索知识库", "基于证据回答"],
  "selected_tools": ["search_kb"],
  "reason": "用户询问企业制度"
}
```

## 4. 执行任务

### Task 1：统一配置

- [x] 在 `test_config.py` 写失败测试：未配置模型时 `llm_enabled=false`，配置环境变量后主/辅助模型分别加载。
- [x] 运行：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests/test_config.py -q
```

预期：因 `enterprise_agent.config` 不存在而失败。

- [x] 实现 `Settings`，至少包含：

```text
LLM_ENABLED
MAIN_LLM_BASE_URL / API_KEY / MODEL / TIMEOUT
MAIN_LLM_FALLBACK_BASE_URL / API_KEY / MODEL
UTILITY_LLM_BASE_URL / API_KEY / MODEL / TIMEOUT
LLM_MAX_ATTEMPTS
```

- [x] 更新 `.env.example`，API Key 只写占位说明。
- [x] Task 1 测试通过。提交由用户执行：

```bash
git add enterprise_agent/config.py enterprise_agent/tests/test_config.py .env.example
git commit -m "feat: add runtime and LLM settings"
```

### Task 2：LLM Contract、OpenAI-compatible Client 与 Fake LLM

- [x] 在 `test_llm_client.py` 写失败测试：
  - Fake LLM 返回固定结构化结果；
  - OpenAI-compatible 响应转换为 `LLMResponse`；
  - 超时映射为 `llm_unavailable`；
  - 非法 JSON 映射为 `llm_invalid_output`；
  - 主 endpoint 失败后调用备用 endpoint。
- [x] 实现 `BaseLLMClient.complete()`、`OpenAICompatibleClient` 和 `FakeLLMClient`。
- [x] 仅允许有限重试；禁止无限循环。
- [x] Task 2 测试通过。提交由用户执行：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests/test_llm_client.py -q
git add enterprise_agent/llm enterprise_agent/tests/test_llm_client.py
git commit -m "feat: add OpenAI compatible LLM gateway"
```

### Task 3：LLM Planner 与规则降级

- [x] 在 `test_llm_planner.py` 写失败测试：
  - 有效结构化输出覆盖规则 Planner；
  - 工具名不在 Registry 时拒绝模型输出；
  - 模型不可用时结果与现有规则 Planner 一致；
  - 模型不能通过输出绕过角色权限。
- [x] 修改 `Planner`，构造方式为：

```python
Planner(llm_client=None, tool_metadata_provider=None)
```

- [x] LLM Planner 只返回任务计划，不执行工具；Router 和 Permission 仍是执行边界。
- [x] 运行现有 Planner 测试和新增测试。提交由用户执行。

### Task 4：LLM Answer Generator 与模板降级

- [x] 在 `test_llm_runtime.py` 写失败测试：
  - LLM 启用时答案来自模型且包含检索来源；
  - 模型答案缺引用时仍被 Verifier 捕获；
  - 模型失败时模板答案保持 M4 行为；
  - SQL 权限拒绝时不得调用答案模型生成虚假数据结论。
- [x] 从 `graph.py` 提取 `AnswerGenerator`，接口为：

```python
class AnswerGenerator:
    def generate(self, state: AgentState) -> tuple[str, dict]:
        ...
```

- [x] `ContextBuilder` 输出作为 LLM evidence context；模型提示明确 evidence-only。
- [x] 将每次模型调用摘要写入 `state["llm_calls"]`。

### Task 5：Trace、CLI 与兼容性

- [x] 扩展 `AgentState` 和 Trace：

```text
llm_calls
llm_fallback_used
prompt_version
```

- [x] CLI 增加 `--llm-enabled/--no-llm` 可选覆盖；默认读取环境变量。
- [x] 确认 Trace 不包含 API Key、Authorization Header 或完整敏感 Prompt。
- [x] 运行 M1-M4 全量测试。

## 5. 验收命令

```bash
cd /mnt/sdc/zxuny/github/harness-engineering
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests/test_config.py enterprise_agent/tests/test_llm_client.py enterprise_agent/tests/test_llm_planner.py enterprise_agent/tests/test_llm_runtime.py -q
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests -q

LLM_ENABLED=false \
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "差旅报销需要哪些材料？" --role employee
```

真实模型验收由用户提供 endpoint 后执行：

```bash
LLM_ENABLED=true \
MAIN_LLM_BASE_URL=http://127.0.0.1:8000/v1 \
MAIN_LLM_API_KEY=local \
MAIN_LLM_MODEL=<configured-model> \
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.app \
  --query "差旅报销需要哪些材料？" --role employee
```

## 6. 验收标准

- [x] 无模型服务时 M4 CLI 和测试继续通过；
- [x] 本地 vLLM 与第三方兼容 API 使用同一客户端；
- [x] 主模型与辅助模型配置互不覆盖；
- [x] LLM Planner 输出经过 schema、工具白名单和权限边界检查；
- [x] LLM Answer 必须接受 Verifier 校验；
- [x] Trace 能区分模型成功、备用 endpoint 和规则降级；
- [x] 代码与文档不包含具体 vLLM 模型硬编码。

## 7. 实际实现补充

真实 vLLM 联调暴露了原设计未覆盖的上下文预算与推理输出问题，因此增加：

- `ContextBuilder` 最多注入 3 条文档，每条最多 240 字符；
- LLM evidence context 总长度限制为 1200 字符；
- 不向答案模型重复注入 `generate_report` 派生报告；
- 清理答案开头的 `<think>...</think>` 推理块；
- 答案提示要求最多展示 5 条记录，其余记录汇总；
- M1-M4 Runtime 测试显式使用 `llm_enabled=False`，避免本地 `.env` 污染；
- 增加 `verifier_history`，保留首次校验和 fallback 后校验结果；
- LLM client 初始化失败也会切换备用 endpoint；
- `.env.example` 已恢复，真实 `.env` 继续由 `.gitignore` 排除。

重试使用显式有限循环实现，没有使用 `tenacity`。该实现满足有限重试要求，且减少了
Gateway 对第三方重试框架的依赖。

## 8. 实际验收结果

自动化测试：

```text
72 passed in 8.58s
```

本地真实 vLLM 已完成以下端到端场景：

| 场景 | 结果 |
| --- | --- |
| 制度问答 | `search_kb` + LLM Answer，成功并包含来源 |
| 8000 元采购审批 | `search_kb + workflow_check`，成功 |
| A 项目风险分析 | `search_kb + generate_report`，成功 |
| 高风险项目统计 | `query_sql + generate_report`，成功 |
| employee 查询业务数据 | `query_sql` 被 `permission_denied` 阻断 |

真实联调验证了：

- OpenAI-compatible vLLM 主模型调用；
- 模型、endpoint、Token、延迟和状态写入 Trace；
- `<think>` 内容不再展示；
- 2048 Token 上下文模型不会因 evidence context 过长而失败；
- 数据分析答案按 5 条明细加剩余数量汇总，不再在输出预算处截断；
- 模型失败时回退 M4 模板答案。

## 9. 尚未执行的外部联调

以下能力已经通过自动化测试，但尚未使用独立真实服务验收：

- `UTILITY_LLM_*` 对应的真实辅助模型 Planner；
- 第二个真实 fallback endpoint；
- 第三方厂商 OpenAI-compatible API。

当前实际 `.env` 仅配置主模型时，运行链路为：

```text
规则 Planner
→ Router
→ Permission
→ Tool Executor
→ Context Builder
→ vLLM Answer Generator
→ Verifier
→ Trace
```

配置 `UTILITY_LLM_BASE_URL`、`UTILITY_LLM_API_KEY` 和 `UTILITY_LLM_MODEL` 后，Planner
会切换为 LLM Planner，并在结构化输出无效或服务不可用时回退规则 Planner。
