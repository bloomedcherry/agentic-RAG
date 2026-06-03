"""Build a lightweight searchable index for enterprise documents."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PACKAGE_ROOT / "data" / "docs"
INDEX_DIR = PACKAGE_ROOT / "data" / "index"
CHUNKS_FILE = "chunks.jsonl"
INDEX_FILE = "tfidf_index.json"
SOURCE_MANIFEST_FILE = "source_manifest.jsonl"

parse_document: Callable[[str], dict] | None = None
chunk_document: Callable[[dict], list[dict]] | None = None

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Tokenize mixed Chinese and ASCII text for the fallback index."""
    tokens = [match.group(0).lower() for match in _TOKEN_RE.finditer(text or "")]
    cjk_chars = [token for token in tokens if len(token) == 1 and "\u4e00" <= token <= "\u9fff"]
    tokens.extend(a + b for a, b in zip(cjk_chars, cjk_chars[1:]))
    return tokens


def iter_document_paths(docs_dir: str | Path = DOCS_DIR) -> Iterable[Path]:
    root = Path(docs_dir)
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}
    )


def _resolve_pipeline_functions() -> tuple[Callable[[str], dict], Callable[[dict], list[dict]]]:
    global parse_document, chunk_document

    if parse_document is None:
        from enterprise_agent.tools.parse_doc import parse_document as imported_parse_document

        parse_document = imported_parse_document

    if chunk_document is None:
        from enterprise_agent.rag.chunker import chunk_document as imported_chunk_document

        chunk_document = imported_chunk_document

    return parse_document, chunk_document


def write_chunks_jsonl(chunks: list[dict], index_dir: str | Path = INDEX_DIR) -> Path:
    output_dir = Path(index_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = output_dir / CHUNKS_FILE
    with chunks_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return chunks_path


def write_index(chunks: list[dict], index_dir: str | Path = INDEX_DIR) -> Path:
    output_dir = Path(index_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_chunks_jsonl(chunks, output_dir)

    token_counts = [Counter(tokenize(chunk.get("content", ""))) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for counts in token_counts:
        document_frequency.update(counts.keys())

    doc_count = len(chunks)
    idf = {
        token: math.log((1 + doc_count) / (1 + frequency)) + 1.0
        for token, frequency in document_frequency.items()
    }
    vectors = []
    for counts in token_counts:
        weighted = {token: count * idf[token] for token, count in counts.items()}
        norm = math.sqrt(sum(value * value for value in weighted.values()))
        vectors.append({"weights": weighted, "norm": norm})

    index_path = output_dir / INDEX_FILE
    index_path.write_text(
        json.dumps(
            {
                "version": 1,
                "backend": "tfidf-fallback",
                "chunks_file": CHUNKS_FILE,
                "idf": idf,
                "vectors": vectors,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return index_path


def load_source_manifest(index_dir: str | Path = INDEX_DIR) -> dict[str, dict]:
    manifest_path = Path(index_dir) / SOURCE_MANIFEST_FILE
    if not manifest_path.exists():
        return {}

    rows = {}
    with manifest_path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            source = row.get("source")
            if source:
                rows[source] = row
    return rows


def _attach_source_metadata(chunks: list[dict], source_manifest: dict[str, dict]) -> list[dict]:
    for chunk in chunks:
        source_meta = source_manifest.get(chunk.get("source"), {})
        if not source_meta:
            continue
        metadata = dict(chunk.get("metadata") or {})
        metadata.update({key: value for key, value in source_meta.items() if key != "source"})
        chunk["metadata"] = metadata
    return chunks


def build_index(
    docs_dir: str | Path = DOCS_DIR,
    index_dir: str | Path = INDEX_DIR,
) -> dict:
    parser, chunker = _resolve_pipeline_functions()
    source_manifest = load_source_manifest(index_dir=index_dir)

    chunks: list[dict] = []
    document_count = 0
    for path in iter_document_paths(docs_dir):
        document_count += 1
        parsed = parser(str(path))
        chunks.extend(chunker(parsed))
    chunks = _attach_source_metadata(chunks, source_manifest)

    index_path = write_index(chunks, index_dir=index_dir)
    return {
        "documents": document_count,
        "chunks": len(chunks),
        "chunks_path": str(Path(index_dir) / CHUNKS_FILE),
        "index_path": str(index_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the enterprise RAG index.")
    parser.add_argument("--docs-dir", default=str(DOCS_DIR))
    parser.add_argument("--index-dir", default=str(INDEX_DIR))
    args = parser.parse_args()

    stats = build_index(docs_dir=args.docs_dir, index_dir=args.index_dir)
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
