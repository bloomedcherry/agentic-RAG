"""Contracts shared by LLM providers and agent components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMRequest:
    messages: list[dict[str, str]]
    response_schema: dict[str, Any] | None = None
    temperature: float = 0.0
    max_tokens: int = 1024


@dataclass
class LLMResponse:
    content: str
    parsed: dict[str, Any] | None
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency: float
    status: str
    error_type: str | None = None
    endpoint: str = "primary"


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return one normalized completion result."""


def llm_call_summary(
    response: LLMResponse,
    *,
    purpose: str,
    prompt_version: str,
    error_type: str | None = None,
) -> dict[str, Any]:
    """Build a trace-safe call summary without prompts or credentials."""

    resolved_error = error_type or response.error_type
    return {
        "purpose": purpose,
        "provider": response.provider,
        "model": response.model,
        "endpoint": response.endpoint,
        "status": "error" if resolved_error else response.status,
        "error_type": resolved_error,
        "prompt_version": prompt_version,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        "latency": response.latency,
    }
