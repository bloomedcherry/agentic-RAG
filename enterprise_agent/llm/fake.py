"""Deterministic LLM client for tests and local smoke checks."""

from __future__ import annotations

from copy import deepcopy

from enterprise_agent.llm.base import BaseLLMClient, LLMRequest, LLMResponse


class FakeLLMClient(BaseLLMClient):
    def __init__(
        self,
        *,
        content: str = "",
        parsed: dict | None = None,
        model: str = "fake-llm",
        status: str = "success",
        error_type: str | None = None,
    ) -> None:
        self.response = LLMResponse(
            content=content,
            parsed=parsed,
            provider="fake",
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            latency=0.0,
            status=status,
            error_type=error_type,
        )
        self.call_count = 0
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        self.requests.append(deepcopy(request))
        return deepcopy(self.response)
