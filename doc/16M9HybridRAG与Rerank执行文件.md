# M9 Hybrid RAG、Query Rewrite 与 Rerank 执行文件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Follow TDD and report measured results without inventing improvements.

**Goal:** 将 TF-IDF baseline 升级为 BM25 + Embedding + Rerank 的混合检索，提升固定 M4/M9 Gold Set 的 Recall@K 和证据质量。

**Architecture:** 稀疏与稠密检索独立构建索引，使用 Reciprocal Rank Fusion 合并候选，再由可配置 Reranker 排序。Utility LLM 可做一次 Query Rewrite，失败时使用原查询。

**Tech Stack:** rank-bm25, sentence-transformers, FAISS, numpy, pytest。

---

## 1. 阶段边界

必须完成：

- BM25 索引；
- Embedding + FAISS 索引；
- Metadata Filter；
- RRF 融合；
- 可开关 Reranker；
- Query Rewrite；
- 增量索引 manifest 和版本；
- 检索消融评估。

本阶段不做：

- 在线训练 embedding/reranker；
- 分布式向量数据库；
- 多模态检索。

## 2. 文件清单

创建：

```text
enterprise_agent/rag/
├── models.py
├── bm25_index.py
├── vector_index.py
├── hybrid_retriever.py
├── reranker.py
├── query_rewriter.py
└── index_manifest.py
enterprise_agent/eval/eval_rag_ablation.py
enterprise_agent/tests/
├── test_bm25_retriever.py
├── test_vector_retriever.py
├── test_hybrid_retriever.py
├── test_reranker.py
├── test_query_rewriter.py
└── test_incremental_index.py
```

修改：

```text
enterprise_agent/rag/build_index.py
enterprise_agent/rag/retriever.py
enterprise_agent/tools/runtime_tools.py
enterprise_agent/config.py
enterprise_agent/data/index/
README.md
```

## 3. 执行任务

### Task 1：统一检索结果结构

- [ ] 定义：

```python
RetrievalHit(
    chunk_id,
    source,
    doc_type,
    content,
    sparse_score,
    dense_score,
    fused_score,
    rerank_score,
)
```

- [ ] 旧 `retrieve()` 返回字段保持兼容。

### Task 2：BM25

- [ ] 测试中文 token、top-k、metadata filter、空查询和确定性排序。
- [ ] 构建 BM25 corpus 和 metadata 文件。

### Task 3：Embedding + FAISS

- [ ] 模型名称配置化，不写死。
- [ ] 测试向量维度、归一化、索引保存/加载、filter 后 top-k。
- [ ] 模型不可用时允许 sparse-only 降级。

### Task 4：Hybrid Fusion

- [ ] 使用 RRF：

```text
score(doc) = Σ 1 / (rrf_k + rank_i)
```

- [ ] 测试 sparse-only、dense-only、hybrid 三种模式。
- [ ] 去重键使用 `chunk_id`。

### Task 5：Reranker

- [ ] 支持：

```text
RERANK_ENABLED
RERANK_MODEL
RERANK_CANDIDATE_K
RERANK_TOP_K
```

- [ ] Reranker 失败时返回 fused 排序并记录降级。

### Task 6：Query Rewrite

- [ ] Utility LLM 最多改写一次；
- [ ] 输出包含 `rewritten_query` 和保留实体；
- [ ] 不允许改写用户金额、项目名或权限意图；
- [ ] 模型失败使用原查询。

### Task 7：增量索引和版本

- [ ] Manifest 记录：

```text
index_version
embedding_model
chunker_version
source checksum
created_at
```

- [ ] 未变化文档不重复 embedding；
- [ ] 删除源文档时清理失效 chunk；
- [ ] 索引构建采用临时目录后原子替换。

### Task 8：Eval 与消融

- [ ] 比较：

```text
TF-IDF
BM25
Embedding
BM25 + Embedding
BM25 + Embedding + Rerank
```

- [ ] 输出 Recall@1/3/5、MRR、平均检索延迟和失败案例。
- [ ] 固定 Gold Set 上 Hybrid Recall@5 必须高于 M4 baseline `0.100`；若未达到，不得宣称完成优化，必须输出失败分析。

## 4. 验收命令

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.build_index
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.eval.eval_rag_ablation \
  --eval-file enterprise_agent/data/eval_tasks.jsonl
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m pytest enterprise_agent/tests -q
```

## 5. 验收标准

- Hybrid 检索接口可替换旧 retriever；
- filters 在 sparse/dense 两路一致；
- 模型不可用时 sparse-only 可运行；
- Rerank 和 rewrite 都有明确降级；
- 索引可增量更新并有版本；
- 固定集 Recall@5 高于 0.100，报告包含真实数值和失败案例。

