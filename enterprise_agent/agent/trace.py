"""JSONL trace logging for runtime executions."""

from __future__ import annotations

import json
import re
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
    record = {
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
        "llm_calls": _llm_calls_for_trace(state.get("llm_calls") or []),
        "llm_fallback_used": bool(state.get("llm_fallback_used", False)),
        "prompt_version": state.get("prompt_version"),
    }
    return _redact_sensitive(record)


def _error_type(state: dict[str, Any], verifier_result: dict[str, Any]) -> str | None:
    issues = verifier_result.get("issues") or []
    if issues:
        return issues[0].get("type")
    for error in state.get("errors") or []:
        if isinstance(error, dict) and error.get("type"):
            return error["type"]
    return None


def _llm_calls_for_trace(calls: list[Any]) -> list[dict[str, Any]]:
    allowed_fields = (
        "purpose",
        "provider",
        "model",
        "endpoint",
        "status",
        "error_type",
        "prompt_version",
        "prompt_tokens",
        "completion_tokens",
        "latency",
    )
    return [
        {key: call.get(key) for key in allowed_fields}
        for call in calls
        if isinstance(call, dict)
    ]


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in {
                "api_key",
                "authorization",
                "headers",
                "messages",
                "prompt",
            }:
                result[key] = "[REDACTED]"
            else:
                result[key] = _redact_sensitive(item)
        return result
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", value)
    return value
