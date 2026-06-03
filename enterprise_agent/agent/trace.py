"""JSONL trace logging for runtime executions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_TRACE_PATH = Path(__file__).resolve().parents[1] / "logs" / "traces.jsonl"


def write_trace(state: dict[str, Any], path: str | Path = DEFAULT_TRACE_PATH) -> str:
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    record = _build_record(state)
    with trace_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(trace_path)


def _build_record(state: dict[str, Any]) -> dict[str, Any]:
    verifier_result = state.get("verifier_result") or {}
    return {
        "task_id": state.get("task_id") or str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": state.get("query", ""),
        "user_role": state.get("role", ""),
        "task_type": state.get("task_type", ""),
        "plan": state.get("plan") or [],
        "tool_calls": state.get("tool_calls") or [],
        "retrieved_docs": state.get("retrieved_docs") or [],
        "tool_outputs": state.get("tool_outputs") or {},
        "answer": state.get("answer", ""),
        "verifier_result": verifier_result,
        "success": bool(verifier_result.get("pass", False)),
        "latency": state.get("latency", 0.0),
        "error_type": _error_type(state, verifier_result),
    }


def _error_type(state: dict[str, Any], verifier_result: dict[str, Any]) -> str | None:
    issues = verifier_result.get("issues") or []
    if issues:
        return issues[0].get("type")
    for error in state.get("errors") or []:
        if isinstance(error, dict) and error.get("type"):
            return error["type"]
    return None
