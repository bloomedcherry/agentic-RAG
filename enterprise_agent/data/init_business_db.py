"""Initialize the small controlled business database used by M2 tools."""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PACKAGE_ROOT / "data" / "business.db"
DEFAULT_PROJECT_DOCS_DIR = PACKAGE_ROOT / "data" / "docs" / "projects"


def parse_project_document(path: str | Path) -> dict:
    source_path = Path(path)
    text = source_path.read_text(encoding="utf-8")
    title = _match_required(r"^\s*#\s+(.+?)档案\s+\d+", text, "project title")
    department = _match_optional(rf"{re.escape(title)}由(.+?)牵头", text) or "未知部门"
    budget = float(_match_optional(r"当前预算基准约为\s*(\d+(?:\.\d+)?)\s*元", text) or 0)
    milestone = _match_optional(r"最近一个里程碑为(.+?)，", text) or "未识别"
    risks = _match_optional(r"当前风险包括(.+?)。", text) or ""
    return {
        "name": title,
        "status": _infer_status(text),
        "risk_level": _infer_risk_level(text),
        "owner": department,
        "budget": budget,
        "source": source_path.name,
        "department": department,
        "milestone": milestone,
        "risks": risks,
    }


def init_business_db(
    db_path: str | Path = DEFAULT_DB_PATH,
    docs_dir: str | Path = DEFAULT_PROJECT_DOCS_DIR,
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [parse_project_document(doc_path) for doc_path in sorted(Path(docs_dir).glob("project_*.md"))]
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE IF EXISTS projects")
        conn.execute(
            """
            CREATE TABLE projects (
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                owner TEXT NOT NULL,
                budget REAL NOT NULL,
                source TEXT PRIMARY KEY,
                department TEXT NOT NULL,
                milestone TEXT NOT NULL,
                risks TEXT NOT NULL
            )
            """
        )
        if rows:
            conn.executemany(
                """
                INSERT INTO projects (
                    name, status, risk_level, owner, budget, source, department, milestone, risks
                )
                VALUES (
                    :name, :status, :risk_level, :owner, :budget, :source,
                    :department, :milestone, :risks
                )
                """,
                rows,
            )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize controlled M2 business data.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--docs-dir", default=str(DEFAULT_PROJECT_DOCS_DIR))
    args = parser.parse_args()
    print(init_business_db(args.db_path, args.docs_dir))


def _match_required(pattern: str, text: str, field_name: str) -> str:
    value = _match_optional(pattern, text)
    if value is None:
        raise ValueError(f"could not parse {field_name}")
    return value


def _match_optional(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else None


def _infer_status(text: str) -> str:
    if any(keyword in text for keyword in ["项目已完成", "状态为已验收", "已验收归档"]):
        return "已验收"
    if any(keyword in text for keyword in ["当前状态为阻塞", "项目阻塞", "状态：阻塞"]):
        return "阻塞"
    return "进行中"


def _infer_risk_level(text: str) -> str:
    if any(keyword in text for keyword in ["高风险", "标红风险", "预算消耗偏高", "延期"]):
        return "高"
    if "风险" in text:
        return "中"
    return "低"


if __name__ == "__main__":
    main()
