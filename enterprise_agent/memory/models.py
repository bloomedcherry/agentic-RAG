"""Data models used by memory backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Session:
    user_id: str
    thread_id: str
    created_at: datetime
    updated_at: datetime
    summary_version: int = 0


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    token_count: int
    seq: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    estimated: bool = True


@dataclass(frozen=True)
class Summary:
    version: int
    covered_until_seq: int
    content: dict[str, Any]
    model: str
    created_at: datetime = field(default_factory=utc_now)
