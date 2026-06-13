from enterprise_agent.agent.verifier import verify


def test_verifier_flags_missing_citation():
    result = verify(
        {
            "task_type": "policy_qa",
            "retrieved_docs": [{"source": "policy.md", "chunk_id": "c1"}],
            "answer": "结论：需要提交发票。",
            "tool_calls": [{"name": "search_kb", "status": "success"}],
        }
    )

    assert result["pass"] is False
    assert result["issues"][0]["type"] == "missing_citation"
    assert result["suggested_action"] == "retry_with_citation"


def test_verifier_accepts_explicit_source_files_from_session_memory():
    result = verify(
        {
            "task_type": "policy_qa",
            "retrieved_docs": [{"source": "policy_016.md", "chunk_id": "c1"}],
            "answer": (
                "# 回答说明\n\n"
                "刚才引用的文件是 `report_008.md`、`report_020.md` 和 "
                "`report_002.md`。"
            ),
            "tool_calls": [{"name": "search_kb", "status": "success"}],
        }
    )

    assert result["pass"] is True
    assert result["issues"] == []
    assert result["suggested_action"] == "none"


def test_verifier_flags_empty_retrieval_for_rag_tasks():
    result = verify(
        {
            "task_type": "policy_qa",
            "retrieved_docs": [],
            "answer": "证据不足。",
            "tool_calls": [{"name": "search_kb", "status": "success"}],
        }
    )

    assert result["pass"] is False
    assert result["issues"][0]["type"] == "retrieval_empty"
    assert result["suggested_action"] == "fallback_insufficient_evidence"


def test_verifier_flags_sql_errors():
    result = verify(
        {
            "task_type": "data_analysis",
            "answer": "# 分析草稿",
            "tool_calls": [{"name": "query_sql", "status": "error"}],
        }
    )

    assert result["pass"] is False
    assert result["issues"][0]["type"] == "sql_error"
    assert result["suggested_action"] == "fallback_without_data_claim"


def test_verifier_flags_permission_violation():
    result = verify(
        {
            "task_type": "data_analysis",
            "answer": "无权调用。",
            "tool_calls": [
                {"name": "query_sql", "status": "permission_denied"},
                {"name": "query_sql", "status": "success"},
            ],
        }
    )

    assert result["pass"] is False
    assert result["issues"][0]["type"] == "permission_violation"
    assert result["suggested_action"] == "refusal"


def test_verifier_flags_report_format_error():
    result = verify(
        {
            "task_type": "project_analysis",
            "retrieved_docs": [{"source": "project.md", "chunk_id": "c1"}],
            "answer": "分析草稿缺少标题\n来源：project.md",
            "tool_calls": [{"name": "generate_report", "status": "success"}],
        }
    )

    assert result["pass"] is False
    assert result["issues"][0]["type"] == "format_error"
    assert result["suggested_action"] == "retry_with_format"
