"""OpenAI-compatible implementation of the LLM contract."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from openai import OpenAI

from enterprise_agent.llm.base import BaseLLMClient, LLMRequest, LLMResponse


@dataclass(frozen=True)
class _Endpoint:
    name: str
    base_url: str
    api_key: str
    model: str


class OpenAICompatibleClient(BaseLLMClient):
    """Call local vLLM or a third-party OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        max_attempts: int = 2,
        fallback_base_url: str | None = None,
        fallback_api_key: str | None = None,
        fallback_model: str | None = None,
        client_factory: Callable[..., Any] = OpenAI,
    ) -> None:
        if not base_url or not model:
            raise ValueError("base_url and model are required")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self.timeout = timeout
        self.max_attempts = max_attempts
        self.client_factory = client_factory
        self.endpoints = [
            _Endpoint("primary", base_url, api_key, model),
        ]
        if fallback_base_url:
            self.endpoints.append(
                _Endpoint(
                    "fallback",
                    fallback_base_url,
                    fallback_api_key or api_key,
                    fallback_model or model,
                )
            )

    def complete(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        last_error: Exception | None = None
        last_endpoint = self.endpoints[0]

        for endpoint in self.endpoints:
            last_endpoint = endpoint
            try:
                client = self.client_factory(
                    base_url=endpoint.base_url,
                    api_key=endpoint.api_key,
                    timeout=self.timeout,
                )
            except Exception as exc:
                last_error = exc
                continue
            for _ in range(self.max_attempts):
                try:
                    raw_response = client.chat.completions.create(
                        **self._request_kwargs(request, endpoint.model)
                    )
                except Exception as exc:
                    last_error = exc
                    continue
                return self._normalize_response(
                    raw_response,
                    request=request,
                    endpoint=endpoint,
                    latency=time.perf_counter() - start,
                )

        return LLMResponse(
            content=str(last_error or "LLM endpoint unavailable"),
            parsed=None,
            provider="openai_compatible",
            model=last_endpoint.model,
            prompt_tokens=0,
            completion_tokens=0,
            latency=time.perf_counter() - start,
            status="error",
            error_type="llm_unavailable",
            endpoint=last_endpoint.name,
        )

    @staticmethod
    def _request_kwargs(request: LLMRequest, model: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    @staticmethod
    def _normalize_response(
        raw_response: Any,
        *,
        request: LLMRequest,
        endpoint: _Endpoint,
        latency: float,
    ) -> LLMResponse:
        content = raw_response.choices[0].message.content or ""
        parsed = None
        if request.response_schema is not None:
            try:
                parsed = json.loads(content)
            except (TypeError, json.JSONDecodeError):
                return LLMResponse(
                    content=content,
                    parsed=None,
                    provider="openai_compatible",
                    model=getattr(raw_response, "model", None) or endpoint.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency=latency,
                    status="error",
                    error_type="llm_invalid_output",
                    endpoint=endpoint.name,
                )

        usage = getattr(raw_response, "usage", None)
        return LLMResponse(
            content=content,
            parsed=parsed,
            provider="openai_compatible",
            model=getattr(raw_response, "model", None) or endpoint.model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency=latency,
            status="success",
            endpoint=endpoint.name,
        )
