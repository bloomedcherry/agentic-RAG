# M5 统一配置与 LLM Gateway 执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. All behavior changes follow TDD.

**Goal:** 接入真实 OpenAI-compatible 主模型和辅助模型，同时保留现有规则 Planner 与模板回答作为稳定降级路径。

**Architecture:** 新增独立 `llm` 包和统一配置层。Planner、Skill Selector、摘要器和答案生成器只依赖项目自己的 `LLMClient`，不直接依赖 OpenAI、vLLM 或具体厂商 SDK。模型不可用或结构化输出无效时，Runtime 回退 M4 规则链路。

**Tech Stack:** Python 3.10, pydantic-settings, openai Python SDK, tenacity, pytest。

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

- [ ] 在 `test_config.py` 写失败测试：未配置模型时 `llm_enabled=false`，配置环境变量后主/辅助模型分别加载。
- [ ] 运行：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests/test_config.py -q
```

预期：因 `enterprise_agent.config` 不存在而失败。

- [ ] 实现 `Settings`，至少包含：

```text
LLM_ENABLED
MAIN_LLM_BASE_URL / API_KEY / MODEL / TIMEOUT
MAIN_LLM_FALLBACK_BASE_URL / API_KEY / MODEL
UTILITY_LLM_BASE_URL / API_KEY / MODEL / TIMEOUT
LLM_MAX_ATTEMPTS
```

- [ ] 更新 `.env.example`，API Key 只写占位说明。
- [ ] 测试通过后提交：

```bash
git add enterprise_agent/config.py enterprise_agent/tests/test_config.py .env.example
git commit -m "feat: add runtime and LLM settings"
```

### Task 2：LLM Contract、OpenAI-compatible Client 与 Fake LLM

- [ ] 在 `test_llm_client.py` 写失败测试：
  - Fake LLM 返回固定结构化结果；
  - OpenAI-compatible 响应转换为 `LLMResponse`；
  - 超时映射为 `llm_unavailable`；
  - 非法 JSON 映射为 `llm_invalid_output`；
  - 主 endpoint 失败后调用备用 endpoint。
- [ ] 实现 `BaseLLMClient.complete()`、`OpenAICompatibleClient` 和 `FakeLLMClient`。
- [ ] 仅允许有限重试；禁止无限循环。
- [ ] 运行并提交：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests/test_llm_client.py -q
git add enterprise_agent/llm enterprise_agent/tests/test_llm_client.py
git commit -m "feat: add OpenAI compatible LLM gateway"
```

### Task 3：LLM Planner 与规则降级

- [ ] 在 `test_llm_planner.py` 写失败测试：
  - 有效结构化输出覆盖规则 Planner；
  - 工具名不在 Registry 时拒绝模型输出；
  - 模型不可用时结果与现有规则 Planner 一致；
  - 模型不能通过输出绕过角色权限。
- [ ] 修改 `Planner`，构造方式为：

```python
Planner(llm_client=None, tool_metadata_provider=None)
```

- [ ] LLM Planner 只返回任务计划，不执行工具；Router 和 Permission 仍是执行边界。
- [ ] 运行现有 Planner 测试和新增测试后提交。

### Task 4：LLM Answer Generator 与模板降级

- [ ] 在 `test_llm_runtime.py` 写失败测试：
  - LLM 启用时答案来自模型且包含检索来源；
  - 模型答案缺引用时仍被 Verifier 捕获；
  - 模型失败时模板答案保持 M4 行为；
  - SQL 权限拒绝时不得调用答案模型生成虚假数据结论。
- [ ] 从 `graph.py` 提取 `AnswerGenerator`，接口为：

```python
class AnswerGenerator:
    def generate(self, state: AgentState) -> tuple[str, dict]:
        ...
```

- [ ] `ContextBuilder` 输出作为 LLM evidence context；模型提示明确 evidence-only。
- [ ] 将每次模型调用摘要写入 `state["llm_calls"]`。

### Task 5：Trace、CLI 与兼容性

- [ ] 扩展 `AgentState` 和 Trace：

```text
llm_calls
llm_fallback_used
prompt_version
```

- [ ] CLI 增加 `--llm-enabled/--no-llm` 可选覆盖；默认读取环境变量。
- [ ] 确认 Trace 不包含 API Key、Authorization Header 或完整敏感 Prompt。
- [ ] 运行 M1-M4 全量测试。

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

- 无模型服务时 M4 CLI 和测试继续通过；
- 本地 vLLM 与第三方兼容 API 使用同一客户端；
- 主模型与辅助模型配置互不覆盖；
- LLM Planner 输出经过 schema、工具白名单和权限边界检查；
- LLM Answer 必须接受 Verifier 校验；
- Trace 能区分模型成功、备用 endpoint 和规则降级；
- 代码与文档不包含具体 vLLM 模型硬编码。

