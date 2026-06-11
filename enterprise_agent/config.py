"""Environment-backed runtime settings."""

from __future__ import annotations

from pydantic import Field
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

    main_llm_fallback_base_url: str | None = None
    main_llm_fallback_api_key: str | None = None
    main_llm_fallback_model: str | None = None

    utility_llm_base_url: str | None = None
    utility_llm_api_key: str | None = None
    utility_llm_model: str | None = None
    utility_llm_timeout: float = Field(default=15.0, gt=0)

    llm_max_attempts: int = Field(default=2, ge=1)
