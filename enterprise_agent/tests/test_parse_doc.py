from pathlib import Path

import pytest

from enterprise_agent.tools.parse_doc import parse_document


def test_parse_markdown_document_extracts_title_and_policy_type(tmp_path: Path) -> None:
    doc_path = tmp_path / "policies" / "travel_rules.md"
    doc_path.parent.mkdir()
    doc_path.write_text("# Travel Reimbursement\n\n## Scope\n\nReceipts are required.\n", encoding="utf-8")

    parsed = parse_document(str(doc_path))

    assert parsed["source"] == "travel_rules.md"
    assert parsed["doc_type"] == "policy"
    assert parsed["title"] == "Travel Reimbursement"
    assert "Receipts are required." in parsed["content"]
    assert parsed["metadata"]["path"] == str(doc_path)
    assert parsed["metadata"]["raw_format"] == "md"


def test_parse_markdown_front_matter_into_metadata(tmp_path: Path) -> None:
    doc_path = tmp_path / "policies" / "policy_from_seed.md"
    doc_path.parent.mkdir()
    doc_path.write_text(
        "---\n"
        "source_url: https://example.com/policy.pdf\n"
        "seed_path: raw/pdf/policy.pdf\n"
        "is_expanded: true\n"
        "---\n"
        "# 差旅制度扩写\n\n## 材料\n需要发票。\n",
        encoding="utf-8",
    )

    parsed = parse_document(str(doc_path))

    assert parsed["title"] == "差旅制度扩写"
    assert parsed["metadata"]["source_url"] == "https://example.com/policy.pdf"
    assert parsed["metadata"]["seed_path"] == "raw/pdf/policy.pdf"
    assert parsed["metadata"]["is_expanded"] is True
    assert "source_url" not in parsed["content"]


def test_parse_text_document_uses_first_non_empty_line_as_title_and_prefix_type(tmp_path: Path) -> None:
    doc_path = tmp_path / "workflow_onboarding.txt"
    doc_path.write_text("\nEmployee Onboarding\n\nCreate account and assign mentor.\n", encoding="utf-8")

    parsed = parse_document(str(doc_path))

    assert parsed["source"] == "workflow_onboarding.txt"
    assert parsed["doc_type"] == "workflow"
    assert parsed["title"] == "Employee Onboarding"
    assert parsed["content"].startswith("Employee Onboarding")


def test_parse_document_defaults_to_general_for_unknown_type(tmp_path: Path) -> None:
    doc_path = tmp_path / "notes.md"
    doc_path.write_text("Loose notes without a markdown title.\n", encoding="utf-8")

    parsed = parse_document(str(doc_path))

    assert parsed["doc_type"] == "general"
    assert parsed["title"] == "notes"


def test_parse_html_document_extracts_visible_text_and_format(tmp_path: Path) -> None:
    doc_path = tmp_path / "meetings" / "meeting_minutes.html"
    doc_path.parent.mkdir()
    doc_path.write_text(
        "<html><head><title>ignore</title><style>.x{}</style></head>"
        "<body><h1>项目会议纪要</h1><p>会议讨论项目风险和采购审批。</p>"
        "<script>ignored()</script></body></html>",
        encoding="utf-8",
    )

    parsed = parse_document(str(doc_path))

    assert parsed["doc_type"] == "meeting"
    assert parsed["title"] == "项目会议纪要"
    assert "项目风险" in parsed["content"]
    assert "ignored" not in parsed["content"]
    assert parsed["metadata"]["raw_format"] == "html"


def test_parse_docx_document_extracts_paragraphs_and_format(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    doc_path = tmp_path / "contracts" / "contract_template.docx"
    doc_path.parent.mkdir()
    document = docx.Document()
    document.add_heading("法律服务合同", level=1)
    document.add_paragraph("合同审批需要业务部门、法务部和财务部确认。")
    document.save(doc_path)

    parsed = parse_document(str(doc_path))

    assert parsed["doc_type"] == "contract"
    assert parsed["title"] == "法律服务合同"
    assert "合同审批" in parsed["content"]
    assert parsed["metadata"]["raw_format"] == "docx"


def test_parse_pdf_document_uses_pdf_extractor_and_format(tmp_path: Path, monkeypatch) -> None:
    doc_path = tmp_path / "policies" / "policy_manual.pdf"
    doc_path.parent.mkdir()
    doc_path.write_bytes(b"%PDF-1.4 fake test bytes")

    monkeypatch.setattr(
        "enterprise_agent.tools.parse_doc._extract_pdf_text",
        lambda path: "员工手册\n差旅报销需要发票和审批单。",
    )

    parsed = parse_document(str(doc_path))

    assert parsed["doc_type"] == "policy"
    assert parsed["title"] == "员工手册"
    assert "差旅报销" in parsed["content"]
    assert parsed["metadata"]["raw_format"] == "pdf"
