## 1. 项目名称推荐

### 推荐名称

**基于 Harness Engineering 的企业 Agentic RAG 知识助手**

### 简历中更简洁的名称

**企业 Agentic RAG 知识助手与可控执行 Harness 系统**

### 不建议使用的名称

不要写成：

* 企业多智能体协作系统
* Agentic RL 企业智能体系统
* MCP 企业智能体平台
* 完整生产级企业 Agent 平台

原因：当前项目定位是 demo 级别的单 Supervisor Agent + Tool/RAG + Harness Runtime，不是复杂多智能体系统。

---

## 2. 项目一句话概括

### 简历版

面向企业内部知识管理与业务流程辅助场景，构建单 Supervisor Agent + 可插拔 Tool/RAG + Harness Runtime 的 Agentic RAG 系统，支持制度问答、流程判断、数据查询和报告草稿生成，并通过 Tool Contract、Verifier、Trace Logging 和 Eval 提升系统可控性与可评估性。

### 面试版

这个项目主要解决企业内部知识分散、流程查询复杂和大模型回答缺少依据的问题。我没有只做普通 RAG，而是设计了一个轻量 Agent Harness，把 RAG 检索、SQL 查询、流程校验、报告生成、权限控制、结果校验和执行日志串成一个可评估的 Agent 执行闭环。

---

## 3. STAR 总体表达

### S：Situation 背景

企业内部知识和业务信息通常分散在制度文档、流程说明、项目资料、会议纪要和结构化数据库中。普通员工、项目经理或运营人员在查询流程、分析项目风险或生成报告时，需要在多个文档和系统之间切换，效率低且容易遗漏信息。普通 RAG 虽然能检索文档并回答问题，但难以处理数据查询、流程判断、权限控制、错误恢复和执行过程复盘等企业场景需求。

### T：Task 任务

设计并实现一个面向企业内部知识管理与业务流程辅助的 Agentic RAG Demo。系统需要在保持 demo 简洁的前提下，支持制度问答、流程判断、项目资料分析、SQL 数据查询和报告草稿生成，并通过 Harness Runtime 管理任务规划、工具路由、上下文组装、权限校验、结果验证、失败重试和执行 Trace。

### A：Action 行动

围绕单 Supervisor Agent 架构，构建了可插拔的 Agent Harness Runtime。首先搭建企业知识库 RAG 链路，完成文档解析、chunk 切分、embedding、向量索引和 top-k 检索；然后设计统一 Tool Contract，将 search_kb、query_sql、workflow_check、generate_report 等工具进行 schema 化封装，支持参数校验、权限控制、风险等级和执行日志记录；接着实现 Planner / Router，根据用户问题自动选择 RAG 或业务工具；同时加入 Verifier / Retry 机制，对引用来源、工具调用、SQL 执行、权限访问和输出格式进行校验；最后设计 Trace Logging 和 Eval Set，从 RAG Recall@K、Tool Call Accuracy、Citation Accuracy、Task Success Rate、Verifier Pass Rate 和 Average Latency 等维度评估系统效果。

### R：Result 结果

项目形成了一个结构清晰、可运行、可扩展的企业 Agentic RAG Demo，能够展示知识检索、工具调用、流程判断、报告生成、执行校验和 Trace 分析等完整链路。通过评测方案和消融实验设计，可以对比 Baseline RAG、RAG + Tool Use、RAG + Verifier 和 Full Harness Runtime 在任务完成率、引用一致性、工具调用准确率和响应延迟上的差异，为后续扩展 Multi-Agent、Agentic RL、Skill 或 MCP 保留接口基础。

如果尚未跑完真实评测结果，简历中不要写具体提升百分比，只写“构建评估体系”和“设计消融实验”。

---

## 4. 简历 Bullet 版本

## 4.1 标准版，适合正常简历项目

* 构建面向企业知识管理与业务流程辅助的 Agentic RAG 系统，采用单 Supervisor Agent + Harness Runtime 架构，支持制度问答、流程判断、项目资料分析、SQL 数据查询和报告草稿生成。

* 设计企业知识库 RAG 链路，完成文档解析、chunk 切分、Embedding 向量化、Top-K 检索和引用溯源，使模型回答能够基于制度文档、项目资料和会议纪要等证据生成。

* 设计统一 Tool Contract，将知识库检索、SQL 查询、流程校验和报告生成工具进行 schema 化封装，支持参数校验、权限控制、风险等级和工具调用 Trace 记录。

* 实现 Agent Harness Runtime，将 Planner / Router、Context Builder、Permission、Verifier、Retry 和 Trace Logging 串联为可控执行流程，提升 Agent 多步任务执行的稳定性和可复盘性。

* 构建 Agent 评估体系，设计企业任务测试集，从 RAG Recall@K、Tool Call Accuracy、Citation Accuracy、Task Success Rate、Verifier Pass Rate 和 Average Latency 等维度评估系统效果。

---

## 4.2 强化版，适合 AI 应用 / Agent 算法岗位

* 面向企业内部知识管理与业务流程辅助场景，构建单 Supervisor Agent + 可插拔 Tool/RAG + Harness Runtime 的 Agentic RAG 系统，实现制度问答、流程判断、项目资料分析、数据查询和报告生成等任务闭环。

* 设计 RAG 检索链路，完成企业制度、流程文档、项目资料和会议纪要的解析、切分、向量化、Top-K 召回和引用溯源，并通过 Citation Accuracy 与 RAG Recall@K 评估检索与回答一致性。

* 设计 Tool Contract 与 Tool Registry，对 search_kb、query_sql、workflow_check、generate_report 等工具统一定义 name、description、input_schema、permission、risk_level 和 retry_policy，提升工具调用的可治理性和可扩展性。

* 实现 Agent Harness Runtime，统一管理任务规划、工具路由、上下文组装、权限校验、结果验证、失败重试和执行 Trace，使 Agent 从单轮问答升级为可控、可观测、可评估的多步任务执行系统。

* 构建 Trace Logging 与 Eval 流程，记录 query、plan、tool_calls、retrieved_docs、tool_outputs、verifier_result、latency 和 error_type，并基于测试集统计任务完成率、工具调用准确率、引用一致率和错误类型分布。

---

## 4.3 简短版，适合简历空间紧张

* 构建企业 Agentic RAG 知识助手，支持制度问答、流程判断、数据查询和报告生成。

* 设计 Tool Contract 与 Harness Runtime，统一管理工具路由、权限校验、结果验证和执行 Trace。

* 构建 RAG、Tool Use、Verifier 和 Eval 流程，从检索命中率、工具调用准确率和任务完成率评估系统效果。

---

## 5. STAR 分点版本

## STAR 1：RAG 与知识库问答

### Situation

企业制度、流程文档、会议纪要和项目资料分散，员工在查询制度或总结项目资料时需要手动检索多个文件，效率低且容易遗漏。

### Task

构建企业知识库 RAG 链路，使 Agent 能基于企业文档检索证据并生成带引用的回答。

### Action

实现文档解析、chunk 切分、metadata 绑定、embedding 向量化和 top-k 检索流程；每个检索结果返回 source、chunk_id、content 和 score，并由 Context Builder 将检索片段组织进模型上下文，最终通过 Verifier 检查回答是否包含引用来源。

### Result

系统能够支持企业制度问答、流程条款检索和项目资料总结，并为每个回答提供可追溯依据。评估上可使用 RAG Recall@K 和 Citation Accuracy 衡量检索命中和引用一致性。

---

## STAR 2：Tool Contract 与工具调用

### Situation

普通 RAG 只能检索文档并回答问题，无法处理 SQL 查询、流程判断和报告生成等需要外部工具参与的任务。

### Task

设计一套统一的工具调用机制，让 Agent 能根据任务类型选择并调用不同业务工具，同时保证工具输入、权限和执行日志可控。

### Action

设计 BaseTool / Tool Contract，为每个工具定义 name、description、input_schema、output_schema、permission、risk_level、timeout 和 retry_policy；将 search_kb、query_sql、workflow_check、generate_report 等能力封装成可注册工具，并由 Router 根据 Planner 输出选择工具调用路径。

### Result

系统从单纯 RAG 问答扩展为 RAG + Tool Use 的任务执行 Agent，能够支持知识检索、业务数据查询、流程校验和报告草稿生成。评估上可使用 Tool Call Accuracy、Tool Success Rate 和 Permission Blocking Accuracy 衡量工具体系效果。

---

## STAR 3：Harness Runtime

### Situation

如果 Agent 只是一个 prompt 加若干工具函数，执行过程容易不可控：模型可能选错工具、缺少引用、越权调用、SQL 执行失败后继续编造结论，并且过程难以复盘。

### Task

设计 Agent Harness Runtime，把任务规划、工具路由、上下文组装、权限控制、结果校验、失败恢复和 Trace 记录统一管理。

### Action

实现 Planner / Router 判断任务类型并选择执行路径；Context Builder 组装用户问题、检索证据、工具输出和输出约束；Permission 模块根据 user_role、tool.permission 和 risk_level 判断是否允许执行；Verifier 检查回答引用、工具调用、SQL 状态和输出格式；Trace Logger 记录每次任务的 query、plan、tool_calls、retrieved_docs、answer、verifier_result 和 latency。

### Result

Agent 执行过程从黑盒生成变成可控、可观测、可复盘的运行流程。后续可以通过 Trace 分析定位检索失败、工具误用、权限拦截和格式错误等问题，并为扩展 Multi-Agent 或轨迹偏好优化提供数据基础。

---

## STAR 4：Verifier / Retry 与安全控制

### Situation

企业知识问答和流程判断需要较高可信度，模型如果没有引用、调用错误工具或越权访问数据，会导致错误建议或安全风险。

### Task

设计结果校验和失败恢复机制，降低无依据回答、工具调用失败和越权访问风险。

### Action

实现 Verifier 检查 missing_citation、retrieval_empty、sql_error、permission_denied、format_error 和 ungrounded_answer 等问题；根据错误类型触发 retry、fallback、refusal 或 human-in-the-loop；对于高风险工具调用，引入 risk_level 和用户确认逻辑；对于权限不足任务，返回明确拒绝而不是继续生成。

### Result

系统具备基础的安全边界和失败恢复能力，可以在缺引用、检索为空、SQL 错误或权限不足时进行拦截和处理。评估上可统计 Verifier Pass Rate、Retry Success Rate、Permission Blocking Accuracy 和 Error Type Distribution。

---

## STAR 5：Trace Logging 与 Eval

### Situation

Agent 系统的失败原因通常来自检索、规划、工具、权限或生成多个环节。如果只看最终回答，很难判断哪个模块导致任务失败。

### Task

构建 Trace Logging 和 Eval 流程，使 Agent 执行过程可记录、可量化、可复盘。

### Action

设计 traces.jsonl 日志格式，记录 task_id、query、user_role、task_type、plan、tool_calls、retrieved_docs、tool_outputs、answer、verifier_result、success、latency 和 error_type；构建 50-100 条企业任务测试集，覆盖制度问答、流程判断、项目资料分析、数据分析和报告生成；设计 eval_rag.py、eval_tool.py、eval_task.py 和 analyze_trace.py 分别评估检索、工具调用、端到端任务和错误分布。

### Result

项目不仅能演示 Agent 执行效果，还能通过 RAG Recall@K、Tool Call Accuracy、Citation Accuracy、Task Success Rate、Verifier Pass Rate 和 Average Latency 量化系统表现，为后续消融实验和简历量化表达提供依据。

---

## 6. 面试自述版本

### 60 秒版本

我做的第二个项目是一个企业 Agentic RAG 知识助手，和第一个微调项目区分开。第一个项目偏模型训练和评估，这个项目偏 AI 应用落地。

这个系统面向企业内部知识管理和业务流程辅助，场景包括制度问答、流程判断、项目资料分析、SQL 数据查询和报告草稿生成。我没有只做普通 RAG，而是设计了单 Supervisor Agent + 可插拔 Tool/RAG + Harness Runtime 架构。Agent 会先判断任务类型，再选择 RAG 检索、SQL 查询、流程校验或报告生成工具，然后把检索证据和工具结果组装进上下文生成回答。

项目里我重点做了 Tool Contract、Verifier、Trace Logging 和 Eval。Tool Contract 用来统一封装工具的 schema、权限和风险等级；Verifier 用来检查回答是否有引用、是否越权、是否存在无依据结论；Trace 记录每次任务的 plan、tool_calls、retrieved_docs 和 verifier_result；Eval 则从 RAG Recall@K、工具调用准确率、引用一致率和任务完成率等维度评估系统效果。

### 2 分钟版本

我这个 Agent 项目主要解决企业内部知识和流程信息分散的问题。比如员工想查报销制度、项目经理想总结会议纪要里的风险、运营人员想查业务数据并生成报告，如果只靠普通大模型，很容易出现无依据回答；如果只做普通 RAG，又不能处理 SQL 查询、流程校验和权限控制。

所以我把项目设计成单 Supervisor Agent + Harness Runtime 的结构。Supervisor Agent 负责判断任务类型和选择工具，底层有 RAG 检索、SQL 查询、流程校验和报告生成等工具。Harness Runtime 负责把这些能力串起来，包括 Planner、Router、Context Builder、Permission、Verifier、Retry 和 Trace Logger。

技术上，RAG 部分负责企业制度、流程文档、项目资料和会议纪要的解析、切分、embedding、top-k 检索和引用溯源。Tool Use 部分我设计了统一 Tool Contract，每个工具都有 name、description、input_schema、output_schema、permission、risk_level 和 retry_policy，这样工具调用不是简单函数调用，而是可以做权限控制、参数校验和审计记录。

为了让系统可评估，我设计了 Trace Logging 和 Eval。每次任务都会记录 query、plan、tool_calls、retrieved_docs、answer、verifier_result、latency 和 error_type。评测上构造企业任务测试集，从 RAG Recall@K、Tool Call Accuracy、Citation Accuracy、Task Success Rate 和 Average Latency 等维度衡量系统效果。这个项目的重点不是训练模型，而是把大模型、知识库、工具和执行约束组织成一个可控、可观测、可评估的 Agent 应用系统。

---

## 7. 面试追问与回答要点

## 问题 1：为什么不只做普通 RAG？

回答要点：

普通 RAG 只能解决“检索文档后回答”的问题，但企业场景里很多任务需要工具调用和流程判断，比如 SQL 查询、审批判断、报告生成和权限控制。这个项目加入 Tool Use 和 Harness Runtime，是为了让 Agent 不只是回答问题，而是能完成多步任务，并且过程可追踪、可校验。

不要说：

“普通 RAG 没用。”

应该说：

“普通 RAG 适合知识问答，但企业流程辅助还需要工具调用、权限和执行校验。”

---

## 问题 2：Harness Engineering 和微调有什么区别？

回答要点：

微调是改模型参数，让模型更适合某类任务；Harness Engineering 不改模型参数，而是优化模型外部的执行系统。它通过任务规划、工具路由、上下文管理、权限控制、Verifier、Retry 和 Trace，让模型在真实业务任务里更稳定、更可控。

一句话：

**微调优化模型本身，Harness 优化 Agent 执行过程。**

---

## 问题 3：为什么当前不是 Multi-Agent？

回答要点：

当前版本定位是 demo，优先实现单 Supervisor Agent + Tool/RAG + Harness Runtime。这样可以先跑通 RAG、工具调用、校验、Trace 和 Eval 的闭环。Multi-Agent 会增加上下文隔离、子 Agent 调度和评估成本，所以我把它作为后续扩展方向，而不是第一版核心。

不要说：

“我实现了完整多智能体协作。”

应该说：

“当前是单主控 Agent，后续可以扩展为 Supervisor + Subagent 架构。”

---

## 问题 4：Tool Contract 有什么作用？

回答要点：

Tool Contract 是为了让工具调用可控。每个工具都统一定义 name、description、input_schema、output_schema、permission、risk_level 和 retry_policy。这样 Router 可以根据工具描述选择工具，Permission 可以根据权限和风险等级拦截工具，Verifier 和 Trace 可以统一分析工具调用是否正确。

---

## 问题 5：Verifier 怎么实现？

回答要点：

第一版 Verifier 主要用规则实现。比如 RAG 任务必须有引用；SQL 工具失败时不能继续生成数据结论；权限不足时必须拒绝；报告生成必须符合固定结构。如果检查失败，就根据错误类型触发 retry、fallback、refusal 或 human-in-the-loop。

后续可以引入 LLM-as-Judge 做更复杂的引用一致性判断。

---

## 问题 6：怎么评估 Agent 效果？

回答要点：

我不只看最终回答，而是分模块评估。RAG 用 Recall@K 衡量正确文档是否召回；Tool Use 用 Tool Call Accuracy 和 Tool Success Rate 衡量工具是否选对和执行成功；回答质量用 Citation Accuracy 和 Task Success Rate；可控性用 Verifier Pass Rate、Retry Success Rate 和 Permission Blocking Accuracy；系统效率用 Average Latency。

当前 M4 已构造 50 条企业任务测试集并跑出一轮实测：RAG Recall@5 为 0.100，Tool Call Accuracy 为 1.000，Permission Blocking Accuracy 为 1.000，Task Success Rate 为 0.960，Citation Accuracy 为 1.000，Verifier Pass Rate 为 0.960，Average Latency 为 0.624527s。这里不写提升百分比，因为还没有做固定 baseline 的对照实验。

---

## 问题 7：如果没有真实企业数据，项目是否可信？

回答要点：

当前是 demo 项目，使用公开真实数据、模板扩展数据、人工精写样例和模拟业务数据库，重点验证架构和执行闭环。简历中不会写成真实生产系统或真实企业内部系统。项目的价值在于展示 Agentic RAG、Tool Use、Harness Runtime、Trace 和 Eval 的工程能力，这些能力可以迁移到真实企业数据场景。

---

## 问题 8：这个项目和第一个微调项目有什么关系？

回答要点：

第一个项目偏模型层，做 SFT、偏好数据、模型评测和推理部署；这个项目偏应用层，做 RAG、工具调用、权限控制、执行校验和评估闭环。两个项目互补：微调项目说明我懂模型适配和评估，Agent 项目说明我能把模型接入知识库和业务工具，做成可运行的应用系统。

---

## 8. 不建议夸大的内容

当前简历中不要写：

* 已实现复杂 Multi-Agent 协作；
* 已实现 Agentic RL；
* 已接入 MCP；
* 已封装 Skill 系统；
* 已上线企业生产环境；
* 已接入真实企业数据库；
* 已实现自进化 Agent 闭环；
* 任务完成率提升 XX%，除非已经真实跑出结果；
* 权限控制达到生产级，除非真的实现完整权限系统。

推荐写法：

* 当前实现单 Supervisor Agent + Tool/RAG + Harness Runtime；
* Multi-Agent / Agentic RL / MCP / Skill 作为后续扩展方向；
* 使用公开真实数据、合成业务流程数据和测试集验证系统闭环；
* 已构建评估体系，实际指标以实验结果为准。

---

## 9. 最终简历推荐版本

### 项目名称

**企业 Agentic RAG 知识助手与可控执行 Harness 系统**

### 项目描述

面向企业内部知识管理与业务流程辅助场景，构建单 Supervisor Agent + 可插拔 Tool/RAG + Harness Runtime 的 Agentic RAG 系统，支持制度问答、流程判断、项目资料分析、SQL 数据查询和报告草稿生成。系统通过 Tool Contract 统一封装知识库检索、SQL 查询、流程校验和报告生成工具，并结合 Verifier、Retry、Permission 和 Trace Logging 提升 Agent 执行过程的可控性、可观测性和可评估性。

### 简历 bullet

* 构建企业 Agentic RAG 知识助手，采用单 Supervisor Agent + Harness Runtime 架构，支持制度问答、流程判断、项目资料分析、SQL 数据查询和报告草稿生成等企业内部任务。

* 设计 RAG 知识库链路，完成企业制度、流程文档、项目资料和会议纪要的解析、切分、向量化、Top-K 检索和引用溯源，使回答能够基于可追踪证据生成。

* 设计统一 Tool Contract，对 search_kb、query_sql、workflow_check、generate_report 等工具进行 schema 化封装，支持参数校验、权限控制、风险等级和工具调用日志记录。

* 实现 Harness Runtime，将 Planner / Router、Context Builder、Permission、Verifier、Retry 和 Trace Logging 串联为可控执行流程，降低无依据回答、工具误用和越权调用风险。

* 构建 Agent 评估体系，设计企业任务测试集，从 RAG Recall@K、Tool Call Accuracy、Citation Accuracy、Task Success Rate、Verifier Pass Rate 和 Average Latency 等维度评估系统效果。

* 构建 50 条企业任务 Eval Set 和 Trace 分析脚本，实测 Tool Call Accuracy 1.000、Permission Blocking Accuracy 1.000、Task Success Rate 0.960、Citation Accuracy 1.000，并通过失败案例定位 TF-IDF 检索召回不足和权限拒绝计分口径问题。

### M4 实测指标说明

| 指标 | 实测值 |
| --- | ---: |
| RAG Recall@5 | 0.100 |
| Tool Call Accuracy | 1.000 |
| Tool Success Rate | 0.978 |
| Permission Blocking Accuracy | 1.000 |
| Task Success Rate | 0.960 |
| Citation Accuracy | 1.000 |
| Verifier Pass Rate | 0.960 |
| Average Latency | 0.624527s |

简历可以写上述实测值，但不要写“相比 baseline 提升 XX%”，因为当前尚未跑正式消融对照。RAG Recall@5 偏低，应如实说明当前检索仍是 TF-IDF baseline，后续可以通过 hybrid retrieval、embedding 和 rerank 优化。
