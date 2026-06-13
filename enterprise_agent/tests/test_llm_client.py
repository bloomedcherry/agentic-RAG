"""Tests for the framework-neutral LLM gateway."""

from __future__ import annotations

from types import SimpleNamespace

from enterprise_agent.llm.base import LLMRequest
from enterprise_agent.llm.client import OpenAICompatibleClient
from enterprise_agent.llm.fake import FakeLLMClient


def _request(structured: bool = True) -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": "classify this request"}],
        response_schema={"type": "object"} if structured else None,
    )


def _sdk_response(content: str, model: str = "served-model") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7),
        model=model,
    )


class _Completions:
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class _SDKClient:
    def __init__(self, outcome) -> None:
        self.chat = SimpleNamespace(completions=_Completions(outcome))


def test_fake_llm_returns_deterministic_structured_response() -> None:
    client = FakeLLMClient(
        content='{"task_type": "policy_qa"}',
        parsed={"task_type": "policy_qa"},
        model="fake-planner",
    )

    first = client.complete(_request())
    second = client.complete(_request())

    assert first.status == "success"
    assert first.parsed == {"task_type": "policy_qa"}
    assert second == first
    assert client.call_count == 2


def test_openai_compatible_response_is_converted_to_llm_response() -> None:
    sdk_client = _SDKClient(_sdk_response('{"task_type": "policy_qa"}'))
    client = OpenAICompatibleClient(
        base_url="http://main.example/v1",
        api_key="secret",
        model="configured-model",
        client_factory=lambda **_: sdk_client,
    )

    response = client.complete(_request())

    assert response.status == "success"
    assert response.parsed == {"task_type": "policy_qa"}
    assert response.provider == "openai_compatible"
    assert response.model == "served-model"
    assert response.prompt_tokens == 11
    assert response.completion_tokens == 7
    assert response.latency >= 0
    assert sdk_client.chat.completions.calls[0]["model"] == "configured-model"


def test_timeout_is_mapped_to_llm_unavailable() -> None:
    client = OpenAICompatibleClient(
        base_url="http://main.example/v1",
        api_key="secret",
        model="main-model",
        max_attempts=1,
        client_factory=lambda **_: _SDKClient(TimeoutError("request timed out")),
    )

    response = client.complete(_request())

    assert response.status == "error"
    assert response.error_type == "llm_unavailable"
    assert "timed out" in response.content


def test_sdk_retries_are_disabled_so_gateway_owns_retry_policy() -> None:
    client_options: list[dict] = []

    def factory(**kwargs):
        client_options.append(kwargs)
        return _SDKClient(_sdk_response('{"task_type": "policy_qa"}'))

    client = OpenAICompatibleClient(
        base_url="http://main.example/v1",
        api_key="secret",
        model="main-model",
        client_factory=factory,
    )

    response = client.complete(_request())

    assert response.status == "success"
    assert client_options[0]["max_retries"] == 0


def test_invalid_json_is_mapped_to_llm_invalid_output() -> None:
    client = OpenAICompatibleClient(
        base_url="http://main.example/v1",
        api_key="secret",
        model="main-model",
        client_factory=lambda **_: _SDKClient(_sdk_response("not-json")),
    )

    response = client.complete(_request())

    assert response.status == "error"
    assert response.error_type == "llm_invalid_output"
    assert response.parsed is None


def test_fallback_endpoint_is_used_after_primary_endpoint_failure() -> None:
    created_urls: list[str] = []

    def factory(**kwargs):
        created_urls.append(kwargs["base_url"])
        if kwargs["base_url"] == "http://main.example/v1":
            return _SDKClient(TimeoutError("primary unavailable"))
        return _SDKClient(_sdk_response('{"task_type": "policy_qa"}', model="fallback-model"))

    client = OpenAICompatibleClient(
        base_url="http://main.example/v1",
        api_key="main-secret",
        model="main-model",
        fallback_base_url="http://fallback.example/v1",
        fallback_api_key="fallback-secret",
        fallback_model="fallback-configured-model",
        max_attempts=1,
        client_factory=factory,
    )

    response = client.complete(_request())

    assert response.status == "success"
    assert response.model == "fallback-model"
    assert response.endpoint == "fallback"
    assert created_urls == ["http://main.example/v1", "http://fallback.example/v1"]


def test_fallback_endpoint_is_used_when_primary_client_initialization_fails() -> None:
    created_urls: list[str] = []

    def factory(**kwargs):
        created_urls.append(kwargs["base_url"])
        if kwargs["base_url"] == "http://main.example/v1":
            raise RuntimeError("invalid primary client configuration")
        return _SDKClient(_sdk_response('{"task_type": "policy_qa"}'))

    client = OpenAICompatibleClient(
        base_url="http://main.example/v1",
        api_key="main-secret",
        model="main-model",
        fallback_base_url="http://fallback.example/v1",
        fallback_api_key="fallback-secret",
        fallback_model="fallback-model",
        max_attempts=1,
        client_factory=factory,
    )

    response = client.complete(_request())

    assert response.status == "success"
    assert response.endpoint == "fallback"
    assert created_urls == ["http://main.example/v1", "http://fallback.example/v1"]
