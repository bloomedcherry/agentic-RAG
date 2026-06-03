import json
import subprocess
import sys
from pathlib import Path

from enterprise_agent.rag.data_builder import build_corpus
from enterprise_agent.rag import build_index, retriever


def test_build_index_recursively_chunks_documents_and_writes_index(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    index_dir = tmp_path / "index"
    (docs_dir / "policies").mkdir(parents=True)
    (docs_dir / "reports").mkdir()
    markdown_doc = docs_dir / "policies" / "travel.md"
    text_doc = docs_dir / "reports" / "summary.txt"
    ignored_doc = docs_dir / "reports" / "image.png"
    markdown_doc.write_text("# 差旅报销制度\n需要发票和行程单。", encoding="utf-8")
    text_doc.write_text("项目周报包含风险、进展和下周计划。", encoding="utf-8")
    ignored_doc.write_text("ignored", encoding="utf-8")

    parsed_paths = []
    chunked_sources = []

    def fake_parse_document(path):
        parsed_paths.append(Path(path).name)
        return {
            "source": Path(path).name,
            "doc_type": Path(path).parent.name.rstrip("s"),
            "title": Path(path).stem,
            "content": Path(path).read_text(encoding="utf-8"),
            "metadata": {"path": str(path)},
        }

    def fake_chunk_document(doc):
        chunked_sources.append(doc["source"])
        return [
            {
                "chunk_id": f"{Path(doc['source']).stem}_chunk_001",
                "source": doc["source"],
                "doc_type": doc["doc_type"],
                "title": doc["title"],
                "content": doc["content"],
                "metadata": {"chunk_index": 1},
            }
        ]

    monkeypatch.setattr(build_index, "parse_document", fake_parse_document)
    monkeypatch.setattr(build_index, "chunk_document", fake_chunk_document)

    stats = build_index.build_index(docs_dir=docs_dir, index_dir=index_dir)

    assert parsed_paths == ["travel.md", "summary.txt"]
    assert chunked_sources == ["travel.md", "summary.txt"]
    assert stats["documents"] == 2
    assert stats["chunks"] == 2

    chunks_path = index_dir / "chunks.jsonl"
    index_path = index_dir / "tfidf_index.json"
    assert chunks_path.exists()
    assert index_path.exists()

    chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines()]
    assert chunks[0]["chunk_id"] == "travel_chunk_001"
    assert chunks[1]["chunk_id"] == "summary_chunk_001"
    assert chunks[0]["content"] == "# 差旅报销制度\n需要发票和行程单。"


def test_retrieve_ranks_chunks_and_applies_filters(tmp_path, monkeypatch):
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    chunks = [
        {
            "chunk_id": "travel_chunk_001",
            "source": "travel.md",
            "doc_type": "policy",
            "title": "差旅报销制度",
            "content": "差旅报销需要提交发票、行程单、审批单和费用明细。",
            "metadata": {"department": "finance"},
        },
        {
            "chunk_id": "contract_chunk_001",
            "source": "contract.md",
            "doc_type": "contract",
            "title": "合同审批流程",
            "content": "合同审批需要法务、财务和业务负责人确认。",
            "metadata": {"department": "legal"},
        },
        {
            "chunk_id": "meeting_chunk_001",
            "source": "meeting.md",
            "doc_type": "meeting",
            "title": "项目例会",
            "content": "项目会议纪要记录风险和待办事项。",
            "metadata": {"department": "project"},
        },
    ]
    build_index.write_index(chunks, index_dir=index_dir)
    monkeypatch.setattr(retriever, "INDEX_DIR", index_dir)

    results = retriever.retrieve("差旅报销需要哪些材料", top_k=2)

    assert [item["chunk_id"] for item in results] == ["travel_chunk_001", "contract_chunk_001"]
    assert set(results[0]) == {"chunk_id", "source", "doc_type", "content", "score"}
    assert results[0]["score"] > results[1]["score"] > 0

    filtered = retriever.retrieve(
        "审批需要哪些部门",
        top_k=5,
        filters={"doc_type": "contract", "metadata": {"department": "legal"}},
    )

    assert [item["chunk_id"] for item in filtered] == ["contract_chunk_001"]


def test_retriever_cli_returns_top_k_json_lines(tmp_path):
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    chunks = [
        {
            "chunk_id": "travel_chunk_001",
            "source": "travel.md",
            "doc_type": "policy",
            "title": "差旅报销制度",
            "content": "差旅报销需要提交发票、行程单、审批单和费用明细。",
            "metadata": {},
        }
    ]
    build_index.write_index(chunks, index_dir=index_dir)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_agent.rag.retriever",
            "--query",
            "差旅报销需要哪些材料",
            "--top-k",
            "1",
            "--index-dir",
            str(index_dir),
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )

    rows = [json.loads(line) for line in completed.stdout.splitlines()]
    assert rows == [
        {
            "chunk_id": "travel_chunk_001",
            "source": "travel.md",
            "doc_type": "policy",
            "content": "差旅报销需要提交发票、行程单、审批单和费用明细。",
            "score": rows[0]["score"],
        }
    ]
    assert rows[0]["score"] > 0


def test_generated_corpus_builds_required_m1_chunk_volume(tmp_path):
    docs_dir = tmp_path / "docs"
    index_dir = tmp_path / "index"

    corpus_stats = build_corpus(output_dir=str(docs_dir), min_docs=300)
    index_stats = build_index.build_index(docs_dir=docs_dir, index_dir=index_dir)

    assert corpus_stats["total_docs"] >= 300
    assert index_stats["documents"] >= 300
    assert index_stats["chunks"] >= 3000
