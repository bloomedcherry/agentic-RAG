"""Environment-backed runtime settings."""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration shared by the CLI, runtime, and LLM gateway."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_enabled: bool = False

    main_llm_base_url: str | None = None
    main_llm_api_key: str | None = None
    main_llm_model: str | None = None
    main_llm_timeout: float = Field(default=30.0, gt=0)
    main_llm_context_window: int = Field(default=128_000, ge=1_024)
    main_llm_max_tokens: int = Field(default=1_024, ge=1)
    agent_max_context_chars: int = Field(default=8_000, ge=1_200)

    main_llm_fallback_base_url: str | None = None
    main_llm_fallback_api_key: str | None = None
    main_llm_fallback_model: str | None = None

    utility_llm_base_url: str | None = None
    utility_llm_api_key: str | None = None
    utility_llm_model: str | None = None
    utility_llm_timeout: float = Field(default=15.0, gt=0)

    llm_max_attempts: int = Field(default=2, ge=1)

    memory_backend: str = "sqlite"
    memory_sqlite_path: str = "enterprise_agent/data/memory.db"
    memory_postgres_url: str | None = None
    memory_max_recent_turns: int = Field(default=10, ge=1)
    memory_max_context_tokens: int = Field(default=2000, ge=100)
    memory_lock_timeout: float = Field(default=10.0, gt=0)

    @model_validator(mode="after")
    def validate_memory_settings(self) -> "Settings":
        backend = self.memory_backend.lower()
        if backend not in {"sqlite", "postgres"}:
            raise ValueError("memory_backend must be sqlite or postgres")
        self.memory_backend = backend
        if backend == "postgres" and not self.memory_postgres_url:
            raise ValueError("memory_postgres_url is required for postgres memory")
        if self.main_llm_max_tokens >= self.main_llm_context_window:
            raise ValueError(
                "main_llm_max_tokens must be smaller than main_llm_context_window"
            )
        return self
