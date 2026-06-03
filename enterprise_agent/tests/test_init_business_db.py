import sqlite3

from enterprise_agent.data.init_business_db import init_business_db, parse_project_document


def test_parse_project_document_extracts_structured_fields(tmp_path):
    project_doc = tmp_path / "project_001.md"
    project_doc.write_text(
        """
        # A 项目档案 001

        ## 项目背景
        A 项目由采购部牵头，目标是在既定预算内完成业务流程优化。
        当前预算基准约为 60000 元，核心约束包括供应商交付。

        ## 当前进展
        最近一个里程碑为接口联调，项目经理已完成进度同步。

        ## 风险清单
        A 项目当前风险包括需求冻结延迟、供应商交付波动和预算消耗偏高。
        若供应商延期超过一周，项目经理需要在周报中标红风险。
        """,
        encoding="utf-8",
    )

    row = parse_project_document(project_doc)

    assert row == {
        "name": "A 项目",
        "status": "进行中",
        "risk_level": "高",
        "owner": "采购部",
        "budget": 60000.0,
        "source": "project_001.md",
        "department": "采购部",
        "milestone": "接口联调",
        "risks": "需求冻结延迟、供应商交付波动和预算消耗偏高",
    }


def test_init_business_db_loads_projects_from_documents_without_seed_rows(tmp_path):
    docs_dir = tmp_path / "projects"
    docs_dir.mkdir()
    (docs_dir / "project_001.md").write_text(
        """
        # A 项目档案 001

        ## 项目背景
        A 项目由采购部牵头，目标是在既定预算内完成业务流程优化。
        当前预算基准约为 60000 元，核心约束包括供应商交付。

        ## 当前进展
        最近一个里程碑为接口联调，项目经理已完成进度同步。

        ## 风险清单
        A 项目当前风险包括需求冻结延迟、供应商交付波动和预算消耗偏高。
        """,
        encoding="utf-8",
    )
    (docs_dir / "project_002.md").write_text(
        """
        # 数据治理专项档案 002

        ## 项目背景
        数据治理专项由项目管理办公室牵头，目标是在既定预算内完成系统交付。
        当前预算基准约为 110000 元，核心约束包括供应商交付。

        ## 当前进展
        最近一个里程碑为用户验收，项目经理已完成进度同步。

        ## 风险清单
        A 项目当前风险包括验收范围不清。
        """,
        encoding="utf-8",
    )

    db_path = init_business_db(db_path=tmp_path / "business.db", docs_dir=docs_dir)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY source")]

    assert [row["name"] for row in rows] == ["A 项目", "数据治理专项"]
    assert rows[0]["source"] == "project_001.md"
    assert rows[1]["owner"] == "项目管理办公室"
    assert rows[1]["risks"] == "验收范围不清"
    assert "B 项目" not in {row["name"] for row in rows}
