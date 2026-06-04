import json

from enterprise_agent.eval.eval_rag import evaluate_rag


def _write_jsonl(path, records):
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def test_evaluate_rag_computes_recall_and_missed_cases(tmp_path):
    eval_file = tmp_path / "eval_tasks.jsonl"
    _write_jsonl(
        eval_file,
        [
            {
                "id": "task_001",
                "query": "差旅报销需要哪些材料？",
                "gold_docs": ["policy_025.md"],
            },
            {
                "id": "task_002",
                "query": "不存在的制度条款",
                "gold_docs": ["missing.md"],
            },
            {
                "id": "task_003",
                "query": "不参与 RAG 统计",
                "gold_docs": [],
            },
        ],
    )

    def fake_retrieve(query, top_k=5):
        if "差旅" in query:
            return [
                {"source": "other.md", "chunk_id": "c0"},
                {"source": "policy_025.md", "chunk_id": "c1"},
            ]
        return [{"source": "other.md", "chunk_id": "c2"}]

    metrics = evaluate_rag(eval_file, retrieve_fn=fake_retrieve)

    assert metrics["total"] == 2
    assert metrics["rag_recall_at_1"] == 0.0
    assert metrics["rag_recall_at_3"] == 0.5
    assert metrics["rag_recall_at_5"] == 0.5
    assert metrics["missed_cases"] == [
        {
            "id": "task_002",
            "query": "不存在的制度条款",
            "gold_docs": ["missing.md"],
            "retrieved_sources": ["other.md"],
        }
    ]
