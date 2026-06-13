"""Incremental session summarization."""

from __future__ import annotations

import json
from typing import Any

from enterprise_agent.llm.base import BaseLLMClient, LLMRequest
from enterprise_agent.memory.models import Message

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "open_items": {"type": "array", "items": {"type": "string"}},
        "referents": {"type": "object"},
    },
    "required": ["facts", "decisions", "open_items", "referents"],
    "additionalProperties": False,
}


class MemorySummarizer:
    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    @property
    def model(self) -> str:
        if self.llm_client is None:
            return "deterministic-summary"
        response = getattr(self.llm_client, "response", None)
        return getattr(response, "model", None) or "utility-llm"

    def summarize(
        self,
        previous_summary: dict[str, Any] | None,
        messages: list[Message],
    ) -> dict[str, Any] | None:
        if not messages:
            return previous_summary
        if self.llm_client is None:
            return _deterministic_summary(previous_summary, messages)

        response = self.llm_client.complete(
            LLMRequest(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Incrementally summarize the session as one JSON object. "
                            "Preserve concrete facts, decisions, unresolved items, and "
                            "referents such as 'the second risk'. Do not invent facts."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "previous_summary": previous_summary,
                                "new_messages": [
                                    {
                                        "seq": message.seq,
                                        "role": message.role,
                                        "content": message.content,
                                    }
                                    for message in messages
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                response_schema=SUMMARY_SCHEMA,
                temperature=0,
                max_tokens=512,
            )
        )
        if response.status != "success" or not isinstance(response.parsed, dict):
            return None
        if not all(
            key in response.parsed
            for key in ("facts", "decisions", "open_items", "referents")
        ):
            return None
        return response.parsed


def _deterministic_summary(
    previous_summary: dict[str, Any] | None,
    messages: list[Message],
) -> dict[str, Any]:
    previous = previous_summary or {}
    facts = list(previous.get("facts") or [])
    for message in messages:
        text = " ".join(message.content.split())
        if text and text not in facts:
            facts.append(text[:240])
    return {
        "facts": facts[-20:],
        "decisions": list(previous.get("decisions") or []),
        "open_items": list(previous.get("open_items") or []),
        "referents": dict(previous.get("referents") or {}),
    }
