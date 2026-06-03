import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


EXPECTED_COUNTS = {
    "policies": 80,
    "workflows": 40,
    "projects": 80,
    "meetings": 80,
    "contracts": 50,
    "reports": 30,
}


def _load_build_corpus():
    spec = importlib.util.find_spec("enterprise_agent.rag.data_builder")
    assert spec is not None, "enterprise_agent.rag.data_builder module should exist"

    module = importlib.import_module("enterprise_agent.rag.data_builder")
    assert hasattr(module, "build_corpus")
    return module.build_corpus


def _digest_docs(docs_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(docs_dir.rglob("*.md")):
        digest.update(path.relative_to(docs_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_build_corpus_generates_required_markdown_and_stats(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    build_corpus = _load_build_corpus()
    raw_dir = tmp_path / "raw"
    (raw_dir / "html" / "policies").mkdir(parents=True)
    (raw_dir / "txt" / "contracts").mkdir(parents=True)
    (raw_dir / "html" / "policies" / "employee_handbook.html").write_text(
        "<h1>员工手册</h1><p>员工差旅报销需要发票和审批单。</p>",
        encoding="utf-8",
    )
    (raw_dir / "html" / "policies" / "employee_handbook.html.meta.json").write_text(
        json.dumps({"source_url": "https://example.com/employee-handbook.html"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (raw_dir / "txt" / "contracts" / "contract_template.txt").write_text(
        "合同示范文本\n合同审批需要业务部门、法务部和财务部确认。",
        encoding="utf-8",
    )
    (raw_dir / "txt" / "contracts" / "contract_template.txt.meta.json").write_text(
        json.dumps({"source_url": "https://example.com/contract-template.txt"}, ensure_ascii=False),
        encoding="utf-8",
    )

    docs_dir = tmp_path / "docs"
    stats = build_corpus(output_dir=str(docs_dir), min_docs=300, raw_dir=str(raw_dir))

    assert stats["total_docs"] == 360
    assert stats["raw_seed_docs"] == 2
    assert stats["by_type"] == {
        "policy": 80,
        "workflow": 40,
        "project": 80,
        "meeting": 80,
        "contract": 50,
        "report": 30,
    }
    assert stats["source_mix"]["public_seed"] > 0
    assert stats["source_mix"]["template_fallback"] == 0
    assert stats["source_counts"]["expanded"] == 360

    for doc_type, expected_count in EXPECTED_COUNTS.items():
        files = sorted((docs_dir / doc_type).glob("*.md"))
        assert len(files) == expected_count

    sample_paths = [
        docs_dir / "policies" / "policy_001.md",
        docs_dir / "workflows" / "workflow_001.md",
        docs_dir / "projects" / "project_001.md",
        docs_dir / "meetings" / "meeting_001.md",
        docs_dir / "contracts" / "contract_001.md",
        docs_dir / "reports" / "report_001.md",
    ]
    for path in sample_paths:
        content = path.read_text(encoding="utf-8")
        assert content.count("\n## ") >= 2
        assert "# " in content
        assert not content.startswith("---")
        assert "source_url:" not in content
        assert "seed_path:" not in content
        assert "raw_format:" not in content
        assert "is_expanded:" not in content
        assert "公开来源摘要" not in content
        assert "公开真实 seed" not in content
        assert "合同审批审批记录" not in content
        assert "知识库扩展条目" not in content
        assert "检索关键词覆盖" not in content
        assert "检索系统应优先返回" not in content

    corpus_text = "\n".join(path.read_text(encoding="utf-8") for path in docs_dir.rglob("*.md"))
    assert "差旅报销" in corpus_text
    assert "8000 元采购申请" in corpus_text
    assert "A 项目" in corpus_text
    assert "合同审批" in corpus_text
    assert "会议纪要生成项目周报" in corpus_text

    stats_path = tmp_path / "enterprise_agent" / "data" / "index" / "corpus_stats.json"
    assert json.loads(stats_path.read_text(encoding="utf-8")) == stats

    manifest_path = tmp_path / "enterprise_agent" / "data" / "index" / "source_manifest.jsonl"
    manifest_rows = [
        json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(manifest_rows) == 360
    assert {"source", "source_url", "seed_path", "raw_format", "is_expanded"} <= set(manifest_rows[0])


def test_build_corpus_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    build_corpus = _load_build_corpus()
    docs_dir = tmp_path / "docs"
    raw_dir = tmp_path / "raw"
    (raw_dir / "txt" / "meetings").mkdir(parents=True)
    (raw_dir / "txt" / "meetings" / "meeting_minutes.txt").write_text(
        "会议纪要\n会议决定推进采购审批和项目风险整改。",
        encoding="utf-8",
    )

    first = build_corpus(output_dir=str(docs_dir), min_docs=300, raw_dir=str(raw_dir))
    first_digest = _digest_docs(docs_dir)

    second = build_corpus(output_dir=str(docs_dir), min_docs=300, raw_dir=str(raw_dir))
    second_digest = _digest_docs(docs_dir)

    assert second == first
    assert second_digest == first_digest


def test_data_builder_cli_accepts_min_docs(tmp_path):
    output_dir = tmp_path / "cli_docs"
    repo_root = Path(__file__).resolve().parents[2]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root),
    }

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_agent.rag.data_builder",
            "--output-dir",
            str(output_dir),
            "--min-docs",
            "300",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    stats = json.loads(result.stdout)
    assert stats["total_docs"] == 360
    assert len(list(output_dir.rglob("*.md"))) == 360
