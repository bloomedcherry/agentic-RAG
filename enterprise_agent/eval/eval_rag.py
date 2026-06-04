"""Evaluate RAG recall against gold document sources."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from enterprise_agent.eval.common import dump_json, read_jsonl
from enterprise_agent.rag.retriever import retrieve


RetrieveFn = Callable[[str, int], list[dict]]


def evaluate_rag(eval_file: str | Path, retrieve_fn: RetrieveFn | None = None) -> dict:
    tasks = read_jsonl(eval_file)
    retrieve_fn = retrieve if retrieve_fn is None else retrieve_fn
    total = 0
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    missed_cases = []

    for task in tasks:
        gold_docs = [str(source) for source in task.get("gold_docs") or []]
        if not gold_docs:
            continue
        total += 1
        docs = retrieve_fn(str(task.get("query", "")), top_k=5)
        retrieved_sources = [str(doc.get("source")) for doc in docs]
        gold = set(gold_docs)
        if gold.intersection(retrieved_sources[:1]):
            hits_at_1 += 1
        if gold.intersection(retrieved_sources[:3]):
            hits_at_3 += 1
        if gold.intersection(retrieved_sources[:5]):
            hits_at_5 += 1
        if not gold.intersection(retrieved_sources[:5]):
            missed_cases.append(
                {
                    "id": task.get("id"),
                    "query": task.get("query", ""),
                    "gold_docs": gold_docs,
                    "retrieved_sources": retrieved_sources[:5],
                }
            )

    return {
        "rag_recall_at_1": _ratio(hits_at_1, total),
        "rag_recall_at_3": _ratio(hits_at_3, total),
        "rag_recall_at_5": _ratio(hits_at_5, total),
        "total": total,
        "missed_cases": missed_cases,
    }


def _ratio(value: int, total: int) -> float:
    return value / total if total else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG recall@k.")
    parser.add_argument("--eval-file", required=True)
    args = parser.parse_args()
    print(dump_json(evaluate_rag(args.eval_file)))


if __name__ == "__main__":
    main()

