# M7 配置式 Skill 与渐进式披露执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Follow TDD.

**Goal:** 在单 Supervisor Agent 中加入可发现、可选择、可执行的配置式 Skill，并通过渐进式披露避免把全部流程、Prompt 和参考资料塞入上下文。

**Architecture:** Skill Registry 只加载轻量元数据；规则预筛选候选，Utility LLM 做结构化最终选择；选中后加载 workflow，执行到具体步骤时才加载对应 Prompt、模板和 reference。无可靠 Skill 时回退通用 Planner/Router。

**Tech Stack:** Python, YAML, Markdown, pydantic, pytest。

---

## 1. 前置条件

- M5 LLM Gateway；
- M6 Memory；
- `PyYAML` 加入环境依赖。

## 2. 第一版 Skill

```text
travel_reimbursement_qa
purchase_approval_check
project_risk_report
```

## 3. 文件清单

创建：

```text
enterprise_agent/skills/
├── __init__.py
├── models.py
├── registry.py
├── loader.py
├── selector.py
├── executor.py
└── definitions/
    ├── travel_reimbursement_qa/
    ├── purchase_approval_check/
    └── project_risk_report/
```

每个 Skill：

```text
SKILL.md
workflow.yaml
prompts/
templates/
references/
```

测试：

```text
test_skill_registry.py
test_skill_loader.py
test_skill_selector.py
test_skill_executor.py
test_skill_runtime.py
```

## 4. Skill Schema

第一层元数据：

```yaml
name: project_risk_report
version: 1.0.0
description: 基于知识库证据生成项目风险报告
task_types: [project_analysis]
keywords: [项目, 风险, 报告]
roles: [manager, admin]
risk_level: low
```

第二层 workflow：

```yaml
input_schema:
  type: object
  required: [query]
allowed_tools: [search_kb, generate_report]
steps:
  - id: retrieve_evidence
    tool: search_kb
    prompt: prompts/retrieve.md
  - id: generate_draft
    tool: generate_report
    prompt: prompts/report.md
output_template: templates/report.md
verifier_rules: [citation_required, markdown_report]
```

## 5. 执行任务

### Task 1：Skill Models 与安全校验

- [ ] 写失败测试覆盖必填字段、版本格式、未知工具、路径穿越和重复 Skill 名。
- [ ] 实现 `SkillMetadata`、`SkillWorkflow`、`SkillStep`。
- [ ] 所有资源路径必须解析在 Skill 目录内，拒绝 `../`。

### Task 2：渐进式 Loader

- [ ] 写失败测试证明：
  - Registry 启动时只读取元数据；
  - 未激活 Skill 时不读取 workflow、prompt 和 reference；
  - 激活后读取 workflow；
  - 执行步骤时才读取该步骤资源。
- [ ] Loader 提供：

```python
load_metadata(path)
load_workflow(skill_name)
load_step_resources(skill_name, step_id)
```

### Task 3：Registry 与候选预筛选

- [ ] 根据 `task_type`、role、关键词、权限、风险等级过滤。
- [ ] 候选为空时返回空列表，不强行选择。
- [ ] 候选排序必须确定性，便于测试和回放。

### Task 4：Utility LLM Selector

- [ ] 写失败测试：
  - LLM 从候选元数据中选择；
  - 输出包含 `skill_name/confidence/reason`；
  - 选择候选外名称时拒绝；
  - 低于阈值时返回 no-skill；
  - Utility LLM 不可用时使用规则最高分候选。
- [ ] Selector 不加载完整 Skill 内容。

### Task 5：通用 Skill Executor

- [ ] 写失败测试：
  - 步骤按顺序执行；
  - 只能调用 `allowed_tools`；
  - 每个工具仍经过 Permission；
  - 前一步失败时按 workflow 策略停止；
  - 输出模板正确；
  - Verifier 规则加入当前 state。
- [ ] Executor 不直接实例化工具，只依赖 `ToolRegistry`。

### Task 6：三个内置 Skill

- [ ] `travel_reimbursement_qa`：

```text
search_kb → evidence-only answer → citation verification
```

- [ ] `purchase_approval_check`：

```text
search_kb → workflow_check → approval answer
```

- [ ] `project_risk_report`：

```text
search_kb → generate_report → markdown/citation verification
```

- [ ] 每个 Skill 至少有一个端到端测试和一个权限/失败测试。

### Task 7：LangGraph 编排

- [ ] 在 Planner 后增加 `skill_selector_node`。
- [ ] 条件边：

```text
selected_skill exists → skill_executor_node
selected_skill absent → router_node
```

- [ ] Skill 完成后进入统一 Context Builder、Answer Generator、Verifier、Memory Writer。
- [ ] State 和 Trace 增加：

```text
skill_candidates
selected_skill
skill_version
skill_steps
skill_fallback_used
```

### Task 8：Eval

- [ ] 扩展 eval task：

```text
expected_skill
expected_skill_steps
```

- [ ] 新增 Skill Selection Accuracy、Skill Completion Rate。
- [ ] 保持 M4 原指标兼容。

## 6. 验收命令

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest \
  enterprise_agent/tests/test_skill_registry.py \
  enterprise_agent/tests/test_skill_loader.py \
  enterprise_agent/tests/test_skill_selector.py \
  enterprise_agent/tests/test_skill_executor.py \
  enterprise_agent/tests/test_skill_runtime.py -q

/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests -q
```

## 7. 验收标准

- Supervisor 初始上下文只包含 Skill 元数据；
- 只有选中 Skill 后才读取 workflow；
- 只有执行步骤时才加载对应 Prompt/reference；
- 三个 Skill 可执行；
- Skill 不能绕过 Tool Registry、Permission 和 Verifier；
- Utility LLM 失败时仍能规则降级；
- 无合适 Skill 时当前通用流程继续运行。

