"""Tests for runtime and LLM environment settings."""

from __future__ import annotations


def test_settings_disable_llm_by_default(monkeypatch) -> None:
    from enterprise_agent.config import Settings

    for name in (
        "LLM_ENABLED",
        "MAIN_LLM_BASE_URL",
        "MAIN_LLM_API_KEY",
        "MAIN_LLM_MODEL",
        "UTILITY_LLM_BASE_URL",
        "UTILITY_LLM_API_KEY",
        "UTILITY_LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_enabled is False
    assert settings.main_llm_model is None
    assert settings.utility_llm_model is None


def test_settings_load_main_utility_and_fallback_models_independently(monkeypatch) -> None:
    from enterprise_agent.config import Settings

    values = {
        "LLM_ENABLED": "true",
        "MAIN_LLM_BASE_URL": "http://main.example/v1",
        "MAIN_LLM_API_KEY": "main-secret",
        "MAIN_LLM_MODEL": "main-model",
        "MAIN_LLM_TIMEOUT": "45",
        "MAIN_LLM_FALLBACK_BASE_URL": "http://fallback.example/v1",
        "MAIN_LLM_FALLBACK_API_KEY": "fallback-secret",
        "MAIN_LLM_FALLBACK_MODEL": "fallback-model",
        "UTILITY_LLM_BASE_URL": "http://utility.example/v1",
        "UTILITY_LLM_API_KEY": "utility-secret",
        "UTILITY_LLM_MODEL": "utility-model",
        "UTILITY_LLM_TIMEOUT": "12",
        "LLM_MAX_ATTEMPTS": "3",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    assert settings.llm_enabled is True
    assert settings.main_llm_base_url == "http://main.example/v1"
    assert settings.main_llm_api_key == "main-secret"
    assert settings.main_llm_model == "main-model"
    assert settings.main_llm_timeout == 45.0
    assert settings.main_llm_fallback_base_url == "http://fallback.example/v1"
    assert settings.main_llm_fallback_api_key == "fallback-secret"
    assert settings.main_llm_fallback_model == "fallback-model"
    assert settings.utility_llm_base_url == "http://utility.example/v1"
    assert settings.utility_llm_api_key == "utility-secret"
    assert settings.utility_llm_model == "utility-model"
    assert settings.utility_llm_timeout == 12.0
    assert settings.llm_max_attempts == 3


def test_runtime_builds_independent_main_and_utility_clients(tmp_path) -> None:
    from enterprise_agent.agent.runtime import Runtime
    from enterprise_agent.config import Settings

    settings = Settings(
        _env_file=None,
        llm_enabled=True,
        main_llm_base_url="http://main.example/v1",
        main_llm_api_key="main-key",
        main_llm_model="main-model",
        main_llm_fallback_base_url="http://fallback.example/v1",
        main_llm_fallback_model="fallback-model",
        utility_llm_base_url="http://utility.example/v1",
        utility_llm_api_key="utility-key",
        utility_llm_model="utility-model",
    )

    runtime = Runtime(settings=settings, trace_path=tmp_path / "trace.jsonl")

    assert runtime.answer_llm_client.endpoints[0].model == "main-model"
    assert runtime.answer_llm_client.endpoints[1].model == "fallback-model"
    assert runtime.planner_llm_client.endpoints[0].model == "utility-model"
    assert runtime.planner_llm_client is not runtime.answer_llm_client

    disabled = Runtime(
        settings=settings,
        llm_enabled=False,
        trace_path=tmp_path / "disabled-trace.jsonl",
    )
    assert disabled.answer_llm_client is None
    assert disabled.planner_llm_client is None


def test_cli_llm_flags_override_environment_default() -> None:
    from enterprise_agent.app import build_parser

    parser = build_parser()

    assert parser.parse_args(["--query", "test"]).llm_enabled is None
    assert parser.parse_args(["--query", "test", "--llm-enabled"]).llm_enabled is True
    assert parser.parse_args(["--query", "test", "--no-llm"]).llm_enabled is False
