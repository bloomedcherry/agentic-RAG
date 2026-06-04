"""Shared JSONL helpers for eval scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fp:
        for line in fp:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def indexed_by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record.get("id") or record.get("task_id")): record for record in records}


def latest_traces_for_tasks(
    traces: list[dict[str, Any]],
    task_ids: set[str],
) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for trace in traces:
        task_id = str(trace.get("task_id"))
        if task_id in task_ids:
            latest[task_id] = trace
    return list(latest.values())
