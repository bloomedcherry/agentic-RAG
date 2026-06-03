from pathlib import Path


def chunk_document(doc: dict, max_chars: int = 240, overlap: int = 30) -> list:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars")

    content = str(doc.get("content", "")).strip()
    if not content:
        return []

    source = doc.get("source", "")
    chunk_prefix = Path(source).stem or "document"
    chunks = []
    start = 0
    chunk_index = 1

    while start < len(content):
        end = min(start + max_chars, len(content))
        chunk_content = content[start:end].strip()
        if chunk_content:
            metadata = dict(doc.get("metadata", {}))
            metadata["chunk_index"] = chunk_index
            chunks.append(
                {
                    "chunk_id": f"{chunk_prefix}_chunk_{chunk_index:03d}",
                    "source": source,
                    "doc_type": doc.get("doc_type", "general"),
                    "title": doc.get("title", ""),
                    "content": chunk_content,
                    "metadata": metadata,
                }
            )
            chunk_index += 1

        if end == len(content):
            break
        start = end - overlap

    return chunks
