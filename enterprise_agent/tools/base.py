"""Framework-neutral tool contract for the enterprise agent runtime."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    backoff_seconds: float = 0.0


@dataclass
class ToolResult:
    status: str
    output: dict[str, Any] | None = None
    error: str | None = None
    latency: float = 0.0


class BaseTool:
    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}
    permission: str = "read"
    risk_level: str = "low"
    timeout: float = 10.0
    retry_policy: RetryPolicy = RetryPolicy()

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "permission": self.permission,
            "risk_level": self.risk_level,
            "timeout": self.timeout,
            "retry_policy": {
                "max_attempts": self.retry_policy.max_attempts,
                "backoff_seconds": self.retry_policy.backoff_seconds,
            },
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        start = time.perf_counter()
        try:
            result = self.run(**kwargs)
            result.latency = time.perf_counter() - start
            return result
        except Exception as exc:
            return ToolResult(
                status="error",
                output=None,
                error=str(exc),
                latency=time.perf_counter() - start,
            )

    def run(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError
