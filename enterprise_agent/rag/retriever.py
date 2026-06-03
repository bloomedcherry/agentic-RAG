"""Retrieve top-k chunks from the lightweight enterprise RAG index."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from enterprise_agent.rag.build_index import CHUNKS_FILE, INDEX_FILE, INDEX_DIR, tokenize


def _load_chunks(index_dir: str | Path) -> list[dict]:
    chunks_path = Path(index_dir) / CHUNKS_FILE
    if not chunks_path.exists():
        raise FileNotFoundError(f"chunks metadata not found: {chunks_path}")
    chunks = []
    with chunks_path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                chunks.append(json.loads(stripped))
    return chunks


def _load_index(index_dir: str | Path) -> dict:
    index_path = Path(index_dir) / INDEX_FILE
    if not index_path.exists():
        raise FileNotFoundError(f"search index not found: {index_path}")
    return json.loads(index_path.read_text(encoding="utf-8"))


def _matches_filters(chunk: dict, filters: dict | None) -> bool:
    if not filters:
        return True

    for key, expected in filters.items():
        if key == "metadata" and isinstance(expected, dict):
            metadata = chunk.get("metadata") or {}
            if any(metadata.get(meta_key) != meta_value for meta_key, meta_value in expected.items()):
                return False
        elif chunk.get(key) != expected:
            return False
    return True


def _query_vector(query: str, idf: dict[str, float]) -> tuple[dict[str, float], float]:
    counts = Counter(tokenize(query))
    weights = {
        token: count * idf[token]
        for token, count in counts.items()
        if token in idf
    }
    norm = math.sqrt(sum(value * value for value in weights.values()))
    return weights, norm


def _score(query_weights: dict[str, float], query_norm: float, vector: dict[str, Any]) -> float:
    doc_norm = vector.get("norm") or 0.0
    if query_norm == 0.0 or doc_norm == 0.0:
        return 0.0

    doc_weights = vector.get("weights") or {}
    dot_product = sum(weight * doc_weights.get(token, 0.0) for token, weight in query_weights.items())
    return dot_product / (query_norm * doc_norm)


def retrieve(
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
    index_dir: str | Path | None = None,
) -> list[dict]:
    index_dir = INDEX_DIR if index_dir is None else index_dir
    chunks = _load_chunks(index_dir)
    index = _load_index(index_dir)
    vectors = index.get("vectors", [])
    query_weights, query_norm = _query_vector(query, index.get("idf", {}))

    ranked = []
    for chunk, vector in zip(chunks, vectors):
        if not _matches_filters(chunk, filters):
            continue
        score = _score(query_weights, query_norm, vector)
        if score <= 0:
            continue
        ranked.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "source": chunk.get("source"),
                "doc_type": chunk.get("doc_type"),
                "content": chunk.get("content"),
                "score": score,
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[: max(top_k, 0)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve chunks from the enterprise RAG index.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--index-dir", default=str(INDEX_DIR))
    args = parser.parse_args()

    for item in retrieve(args.query, top_k=args.top_k, index_dir=args.index_dir):
        print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
