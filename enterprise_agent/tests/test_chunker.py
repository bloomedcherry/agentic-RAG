from enterprise_agent.rag.chunker import chunk_document


def test_chunk_document_returns_metadata_and_incrementing_ids() -> None:
    doc = {
        "source": "policy_travel.md",
        "doc_type": "policy",
        "title": "Travel Policy",
        "content": "A" * 90 + " " + "B" * 90 + " " + "C" * 90,
        "metadata": {"path": "/tmp/policy_travel.md"},
    }

    chunks = chunk_document(doc, max_chars=120, overlap=20)

    assert len(chunks) >= 2
    assert [chunk["chunk_id"] for chunk in chunks] == [
        f"policy_travel_chunk_{index:03d}" for index in range(1, len(chunks) + 1)
    ]
    for index, chunk in enumerate(chunks, start=1):
        assert chunk["source"] == "policy_travel.md"
        assert chunk["doc_type"] == "policy"
        assert chunk["title"] == "Travel Policy"
        assert chunk["content"]
        assert len(chunk["content"]) <= 120
        assert chunk["metadata"]["path"] == "/tmp/policy_travel.md"
        assert chunk["metadata"]["chunk_index"] == index


def test_chunk_document_preserves_configured_overlap() -> None:
    doc = {
        "source": "meeting_notes.txt",
        "doc_type": "meeting",
        "title": "Planning Meeting",
        "content": "0123456789" * 12,
        "metadata": {},
    }

    chunks = chunk_document(doc, max_chars=50, overlap=10)

    assert chunks[0]["content"][-10:] == chunks[1]["content"][:10]


def test_chunk_document_skips_empty_content() -> None:
    doc = {
        "source": "empty.md",
        "doc_type": "general",
        "title": "Empty",
        "content": "   \n\n\t",
        "metadata": {},
    }

    assert chunk_document(doc) == []
