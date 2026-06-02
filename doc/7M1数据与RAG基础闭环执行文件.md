# M1 数据与 RAG 基础闭环执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建中等规模半真实企业知识库，并跑通 RAG 子系统的解析、切分、索引和 top-k 检索闭环。

**Architecture:** M1 不接完整 Agent Runtime，只实现 RAG 子系统。`rag/data_builder.py` 负责公开采样、模板扩展和人工样例标准化，`tools/parse_doc.py` 负责文档解析，`rag/chunker.py` 负责 chunk 与 metadata，`rag/build_index.py` 负责 embedding 和索引构建，`rag/retriever.py` 负责检索并返回 `source/chunk_id/content/score`。

**Tech Stack:** Python, Markdown/TXT, FAISS 或 Chroma, sentence-transformers/bge embedding, pytest。

---

## 1. 本阶段边界

本阶段必须完成：

* `data/docs/` 中准备 300+ 篇半真实企业文档；
* `data/index/chunks.jsonl` 中生成 3,000+ chunks；
* 数据来源包含公开采样、模板扩展和人工精写样例；
* 支持 Markdown / TXT 文档解析；
* 每个 chunk 保留 `chunk_id`、`source`、`doc_type`、`title`、`content`、`metadata`；
* 构建 `data/index/` 下的向量索引和 chunks metadata；
* `python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料"` 能返回检索结果。

本阶段不做：

* Planner / Router；
* Tool Contract；
* LLM 生成；
* Verifier / Retry；
* Eval 指标统计。

---

## 2. 文件清单

创建：

```text
enterprise_agent/
├── __init__.py
├── tools/
│   ├── __init__.py
│   └── parse_doc.py
├── rag/
│   ├── __init__.py
│   ├── data_builder.py
│   ├── chunker.py
│   ├── build_index.py
│   └── retriever.py
├── data/
│   ├── raw/
│   ├── generators/
│   ├── docs/
│   └── index/
└── tests/
    ├── test_data_builder.py
    ├── test_parse_doc.py
    ├── test_chunker.py
    └── test_retriever.py
```

修改：

```text
requirements.txt
README.md
```

---

## 3. 执行任务

### Task 1: 初始化工程目录

- [ ] 创建 `enterprise_agent/`、`enterprise_agent/tools/`、`enterprise_agent/rag/`、`enterprise_agent/data/raw/`、`enterprise_agent/data/generators/`、`enterprise_agent/data/docs/`、`enterprise_agent/data/index/`、`enterprise_agent/tests/`。
- [ ] 创建 `__init__.py`，保证后续可以用 `python -m enterprise_agent...` 执行模块。
- [ ] 在 `README.md` 增加 M1 运行命令：

```bash
python -m enterprise_agent.rag.data_builder --min-docs 300
python -m enterprise_agent.rag.build_index
python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
```

### Task 2: 构建中等规模半真实企业文档

- [ ] 在 `enterprise_agent/data/docs/` 准备 6 类文档：

```text
policies/
workflows/
projects/
meetings/
contracts/
reports/
```

- [ ] 文档规模满足最低验收：

```text
policies   >= 80 篇
workflows  >= 40 篇
projects   >= 80 篇
meetings   >= 80 篇
contracts  >= 50 篇
reports    >= 30 篇
总文档数   >= 300 篇
```

- [ ] 数据来源比例目标：

```text
公开真实数据：30%-40%
模板扩展数据：50%-60%
人工精写数据：10%
```

- [ ] 每篇文档至少包含一个一级标题、两个二级标题和可检索的制度/流程/项目内容。
- [ ] 确保文档能支撑这些查询：

```text
差旅报销需要哪些材料？
8000 元采购申请是否需要审批？
A 项目当前有哪些风险？
合同审批需要经过哪些部门？
根据会议纪要生成项目周报需要包含哪些部分？
```

### Task 3: 实现数据构建器

文件：`enterprise_agent/rag/data_builder.py`

- [ ] 实现 `build_corpus(output_dir: str = "enterprise_agent/data/docs") -> dict`。
- [ ] 从 `enterprise_agent/data/raw/` 读取公开采样数据。
- [ ] 从 `enterprise_agent/data/generators/` 读取模板配置。
- [ ] 批量生成 policies、workflows、projects、meetings、contracts、reports 六类 Markdown。
- [ ] 写入 `enterprise_agent/data/index/corpus_stats.json`：

```python
{
    "total_docs": 360,
    "by_type": {
        "policy": 80,
        "workflow": 40,
        "project": 80,
        "meeting": 80,
        "contract": 50,
        "report": 30
    },
    "source_mix": {
        "public": 0.35,
        "template": 0.55,
        "manual": 0.10
    }
}
```

- [ ] 支持 CLI：

```bash
python -m enterprise_agent.rag.data_builder --min-docs 300
```

### Task 4: 实现文档解析

文件：`enterprise_agent/tools/parse_doc.py`

- [ ] 实现 `parse_document(path: str) -> dict`。
- [ ] 返回结构：

```python
{
    "source": "policy_reimbursement.md",
    "doc_type": "policy",
    "title": "差旅报销制度",
    "content": "...",
    "metadata": {"path": "..."}
}
```

- [ ] `doc_type` 根据文件名前缀判断：

```text
policies/* 或 policy_* -> policy
workflows/* 或 workflow_* -> workflow
projects/* 或 project_* -> project
meetings/* 或 meeting_* -> meeting
contracts/* 或 contract_* -> contract
reports/* 或 report_* -> report
其他 -> general
```

### Task 5: 实现 chunker

文件：`enterprise_agent/rag/chunker.py`

- [ ] 实现 `chunk_document(doc: dict, max_chars: int = 800, overlap: int = 80) -> list[dict]`。
- [ ] 每个 chunk 必须包含：

```python
{
    "chunk_id": "policy_reimbursement_chunk_001",
    "source": "policy_reimbursement.md",
    "doc_type": "policy",
    "title": "差旅报销制度",
    "content": "...",
    "metadata": {"chunk_index": 1}
}
```

- [ ] chunk 不允许为空，`chunk_id` 在同一文档内递增。

### Task 6: 实现索引构建

文件：`enterprise_agent/rag/build_index.py`

- [ ] 递归读取 `enterprise_agent/data/docs/` 下所有 `.md` 和 `.txt`。
- [ ] 调用 `parse_document` 和 `chunk_document`。
- [ ] 生成 `enterprise_agent/data/index/chunks.jsonl`。
- [ ] 确保 `chunks.jsonl` 至少 3,000 行。
- [ ] 构建向量索引，保存到 `enterprise_agent/data/index/`。
- [ ] 如果暂时没有 FAISS / Chroma，可先使用 TF-IDF 或 embedding cosine 作为可运行 fallback，但接口保持不变。

### Task 7: 实现 retriever

文件：`enterprise_agent/rag/retriever.py`

- [ ] 实现：

```python
def retrieve(query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
    ...
```

- [ ] 返回字段：

```python
[
    {
        "chunk_id": "...",
        "source": "...",
        "doc_type": "...",
        "content": "...",
        "score": 0.82
    }
]
```

- [ ] 支持 CLI：

```bash
python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
```

### Task 8: 测试

- [ ] `tests/test_data_builder.py` 覆盖文档数量、类别分布、`corpus_stats.json`。
- [ ] `tests/test_parse_doc.py` 覆盖标题、doc_type、content 解析。
- [ ] `tests/test_chunker.py` 覆盖 chunk 非空、chunk_id、metadata。
- [ ] `tests/test_retriever.py` 覆盖检索结果包含 `source/chunk_id/content/score`。
- [ ] 运行：

```bash
pytest enterprise_agent/tests/test_data_builder.py enterprise_agent/tests/test_parse_doc.py enterprise_agent/tests/test_chunker.py enterprise_agent/tests/test_retriever.py -q
```

---

## 4. 验收标准

M1 完成后必须满足：

```bash
python -m enterprise_agent.rag.data_builder --min-docs 300
python -m enterprise_agent.rag.build_index
python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
pytest enterprise_agent/tests/test_data_builder.py enterprise_agent/tests/test_parse_doc.py enterprise_agent/tests/test_chunker.py enterprise_agent/tests/test_retriever.py -q
```

期望：

* `enterprise_agent/data/docs/` 至少 300 篇文档；
* `enterprise_agent/data/index/chunks.jsonl` 至少 3,000 行；
* `enterprise_agent/data/index/corpus_stats.json` 存在；
* 检索输出至少 3 条结果；
* 每条结果包含 `source`、`chunk_id`、`content`、`score`；
* `data/index/chunks.jsonl` 存在；
* 测试通过。

---

## 5. 同步记录

执行同步时记录：

```text
日期：
执行人：
完成步骤：
生成文件：
验证命令：
验证结果：
阻塞问题：
下一步：
```
