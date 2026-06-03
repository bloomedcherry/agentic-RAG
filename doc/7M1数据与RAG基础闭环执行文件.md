# M1 数据与 RAG 基础闭环执行文件

> 状态：已完成。本文档记录 M1 的实际执行结果、复现命令和验收结果。

**Goal:** 构建基于公开真实 seed 的企业规章知识库，跑通 RAG 子系统的原始文档解析、扩写文档生成、chunk、索引和 top-k 检索闭环。

**Architecture:** M1 不接完整 Agent Runtime，只实现 RAG 子系统。`rag/download_raw_data.py` 下载公开 raw seed，`tools/parse_doc.py` 解析 Markdown / TXT / PDF / DOCX / HTML，`rag/data_builder.py` 基于真实 seed 生成企业规章 Markdown，`rag/chunker.py` 生成 chunks，`rag/build_index.py` 写入 chunks 和 TF-IDF fallback 索引，`rag/retriever.py` 返回 `source/chunk_id/doc_type/content/score`。

**Runtime:** 使用项目 conda 环境：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python
```

联网下载或安装依赖时使用 27890 代理端口和镜像源。

---

## 1. 本阶段边界

本阶段已完成：

* `enterprise_agent/data/raw/` 中准备公开真实 raw seed，覆盖 PDF / DOCX / DOC / HTML；
* 支持 Markdown / TXT / PDF / DOCX / HTML 文档解析；
* `enterprise_agent/data/docs/` 中生成 360 篇企业规章 Markdown；
* 文档正文保持企业规章风格，不包含 `source_url`、`seed_path`、`raw_format`、公开来源说明等技术 metadata；
* 来源信息单独写入 `enterprise_agent/data/index/source_manifest.jsonl`；
* `enterprise_agent/data/index/chunks.jsonl` 生成 3,297 chunks；
* 每个 chunk 保留 `chunk_id`、`source`、`doc_type`、`title`、`content`、`metadata`；
* chunk metadata 合并 `source_url`、`seed_path`、`raw_format`、`is_expanded`；
* 构建 `enterprise_agent/data/index/tfidf_index.json`；
* `retriever` CLI 可返回 top-k 检索结果。

本阶段不做：

* Planner / Router；
* Tool Contract；
* LLM 生成；
* Verifier / Retry；
* Eval 指标统计；
* FAISS / Chroma / embedding 索引替换。

当前索引实现说明：

* 已实现标准库 TF-IDF fallback；
* M1 执行文件允许 fallback；
* M2/M3 后可替换为 `sentence-transformers + FAISS/Chroma`。

---

## 2. 文件清单

已创建 / 修改：

```text
enterprise_agent/
├── __init__.py
├── tools/
│   ├── __init__.py
│   └── parse_doc.py
├── rag/
│   ├── __init__.py
│   ├── download_raw_data.py
│   ├── data_builder.py
│   ├── chunker.py
│   ├── build_index.py
│   └── retriever.py
├── data/
│   ├── raw/
│   │   ├── source_manifest.json
│   │   ├── source_manifest_reports.json
│   │   ├── pdf/
│   │   ├── docx/
│   │   ├── doc/
│   │   └── html/
│   ├── docs/
│   │   ├── policies/
│   │   ├── workflows/
│   │   ├── projects/
│   │   ├── meetings/
│   │   ├── contracts/
│   │   └── reports/
│   └── index/
│       ├── corpus_stats.json
│       ├── source_manifest.jsonl
│       ├── chunks.jsonl
│       └── tfidf_index.json
└── tests/
    ├── test_data_builder.py
    ├── test_parse_doc.py
    ├── test_chunker.py
    └── test_retriever.py
```

同时更新：

```text
README.md
requirements.txt
```

---

## 3. 执行任务

### Task 1: 初始化工程目录

- [x] 创建 `enterprise_agent/`、`enterprise_agent/tools/`、`enterprise_agent/rag/`、`enterprise_agent/data/raw/`、`enterprise_agent/data/docs/`、`enterprise_agent/data/index/`、`enterprise_agent/tests/`。
- [x] 创建 `__init__.py`，支持 `python -m enterprise_agent...`。
- [x] 在 `README.md` 增加 M1 运行命令。

### Task 2: 下载公开真实 raw seed

- [x] 新增 `enterprise_agent/rag/download_raw_data.py`。
- [x] 新增 `enterprise_agent/data/raw/source_manifest.json`。
- [x] 下载公开 PDF / DOCX / DOC / HTML raw 文件。
- [x] 为 raw 文件写入 `.meta.json`，记录 `source_url`、`source_name`、`declared_doc_type`。
- [x] 安装并使用 `PyMuPDF` 加速 PDF 解析。

当前 raw 覆盖：

```text
policy    PDF / HTML
workflow  PDF
project   HTML
meeting   PDF / DOCX / HTML
contract  PDF / DOCX / DOC / HTML
report    PDF / HTML
```

### Task 3: 构建企业规章 Markdown

- [x] 在 `enterprise_agent/data/docs/` 准备 6 类文档：

```text
policies/
workflows/
projects/
meetings/
contracts/
reports/
```

- [x] 文档规模满足验收：

```text
policies   = 80 篇
workflows  = 40 篇
projects   = 80 篇
meetings   = 80 篇
contracts  = 50 篇
reports    = 30 篇
总文档数   = 360 篇
```

- [x] 所有文档基于 public seed 扩写：

```json
{
  "raw_seed_docs": 13,
  "source_mix": {
    "public_seed": 1.0,
    "template_fallback": 0.0
  },
  "source_counts": {
    "expanded": 360,
    "public_seed_docs": 360,
    "template_fallback_docs": 0
  }
}
```

- [x] 文档正文为企业规章风格。
- [x] 文档正文不包含来源 front matter 或公开来源介绍。
- [x] 禁止生成以下模板痕迹：

```text
知识库扩展条目
检索关键词覆盖
检索系统应优先返回
公开来源摘要
公开真实 seed
source_url
seed_path
raw_format
is_expanded
```

- [x] 合同类标题修正为规章标题，例如：

```text
# 合同审批管理规程 001
```

### Task 4: 实现文档解析

文件：`enterprise_agent/tools/parse_doc.py`

- [x] 实现 `parse_document(path: str) -> dict`。
- [x] 支持 `.md`、`.txt`、`.pdf`、`.docx`、`.html`、`.htm`。
- [x] PDF 优先使用 `PyMuPDF/fitz`，失败时 fallback 到 `pypdf`。
- [x] DOCX 使用 `python-docx`。
- [x] HTML 使用 `beautifulsoup4`。
- [x] 支持 front matter 解析，但生成后的企业规章 Markdown 不再写 front matter。
- [x] `doc_type` 根据目录名或文件名前缀判断。

返回结构：

```python
{
    "source": "contract_001.md",
    "doc_type": "contract",
    "title": "合同审批管理规程 001",
    "content": "...",
    "metadata": {"path": "...", "raw_format": "md"}
}
```

### Task 5: 实现 chunker

文件：`enterprise_agent/rag/chunker.py`

- [x] 实现 `chunk_document(doc: dict, max_chars: int = 240, overlap: int = 30) -> list[dict]`。
- [x] 每个 chunk 包含：

```python
{
    "chunk_id": "contract_001_chunk_001",
    "source": "contract_001.md",
    "doc_type": "contract",
    "title": "合同审批管理规程 001",
    "content": "...",
    "metadata": {"chunk_index": 1}
}
```

- [x] chunk 不允许为空。
- [x] `chunk_id` 在同一文档内递增。

说明：

* 默认 chunk 粒度从 800 调整为 240；
* 原因是企业规章文档已去除模板堆叠，较小 chunk 更适合 RAG 检索，也能保持 3,000+ chunks 的 M1 体量。

### Task 6: 实现索引构建

文件：`enterprise_agent/rag/build_index.py`

- [x] 递归读取 `enterprise_agent/data/docs/` 下所有 `.md` 和 `.txt`。
- [x] 调用 `parse_document` 和 `chunk_document`。
- [x] 读取 `enterprise_agent/data/index/source_manifest.jsonl`。
- [x] 将 `source_url`、`seed_path`、`raw_format`、`is_expanded` 合并到 chunk metadata。
- [x] 生成 `enterprise_agent/data/index/chunks.jsonl`。
- [x] `chunks.jsonl` 达到 3,297 行。
- [x] 构建 TF-IDF fallback 索引，保存到 `enterprise_agent/data/index/tfidf_index.json`。

### Task 7: 实现 retriever

文件：`enterprise_agent/rag/retriever.py`

- [x] 实现：

```python
def retrieve(query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
    ...
```

- [x] 返回字段：

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

- [x] 支持 CLI：

```bash
python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
```

### Task 8: 测试

- [x] `tests/test_data_builder.py` 覆盖文档数量、类别分布、`corpus_stats.json`、`source_manifest.jsonl`、正文无来源字段和无模板痕迹。
- [x] `tests/test_parse_doc.py` 覆盖 Markdown / TXT / HTML / DOCX / PDF 标题、doc_type、content 和 metadata 解析。
- [x] `tests/test_chunker.py` 覆盖 chunk 非空、chunk_id、metadata。
- [x] `tests/test_retriever.py` 覆盖索引构建、检索排序、filters、CLI、3,000+ chunks。

---

## 4. 复现命令

使用项目 conda 环境：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.download_raw_data
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.data_builder --min-docs 300
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.build_index
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests -q
```

联网下载或安装依赖时使用：

```bash
export HTTP_PROXY=http://127.0.0.1:27890
export HTTPS_PROXY=http://127.0.0.1:27890
export ALL_PROXY=socks5://127.0.0.1:27890
export http_proxy=http://127.0.0.1:27890
export https_proxy=http://127.0.0.1:27890
export all_proxy=socks5://127.0.0.1:27890
```

安装依赖示例：

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pip install \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  --trusted-host pypi.tuna.tsinghua.edu.cn \
  pymupdf
```

---

## 5. 验收结果

最新验收结果：

```text
data/docs 文档数：360
policies: 80
workflows: 40
projects: 80
meetings: 80
contracts: 50
reports: 30
raw_seed_docs: 13
chunks.jsonl: 3297 chunks
pytest: 17 passed
```

正文检查：

```bash
rg "source_url|seed_path|raw_format|is_expanded|公开来源摘要|公开真实 seed|合同审批审批记录" enterprise_agent/data/docs
```

结果：无匹配。

样例标题：

```text
# 合同审批管理规程 001
```

chunk metadata 样例保留来源：

```python
{
    "source_url": "...",
    "seed_path": "...",
    "raw_format": "docx",
    "is_expanded": True
}
```

---

## 6. 同步记录

```text
日期：2026-06-03
执行人：Codex
完成步骤：
  - 初始化 M1 工程目录
  - 下载公开 raw seed
  - 支持 PDF / DOCX / HTML 解析
  - 使用 PyMuPDF 解析 PDF
  - 生成 360 篇企业规章 Markdown
  - 将来源信息移出正文，写入 source_manifest.jsonl
  - 构建 3297 chunks 和 TF-IDF fallback 索引
  - 完成 retriever CLI
生成文件：
  - enterprise_agent/rag/download_raw_data.py
  - enterprise_agent/rag/data_builder.py
  - enterprise_agent/rag/chunker.py
  - enterprise_agent/rag/build_index.py
  - enterprise_agent/rag/retriever.py
  - enterprise_agent/tools/parse_doc.py
  - enterprise_agent/data/raw/
  - enterprise_agent/data/docs/
  - enterprise_agent/data/index/
验证命令：
  - /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.data_builder --min-docs 300
  - /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.build_index
  - /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.retriever --query "合同审批需要经过哪些部门" --top-k 2
  - env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests -q
验证结果：
  - 360 documents
  - 3297 chunks
  - 17 passed
阻塞问题：
  - 无当前阻塞
下一步：
  - 进入 M2：Tool Contract 与 Agent Runtime
```
