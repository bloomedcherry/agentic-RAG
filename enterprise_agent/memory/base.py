"""Storage contract for session memory."""

from __future__ import annotations

from typing import Protocol

from enterprise_agent.memory.models import Message, Session, Summary


class MemoryStore(Protocol):
    def create_or_touch_session(self, user_id: str, thread_id: str) -> Session: ...

    def append_message(
        self, user_id: str, thread_id: str, message: Message
    ) -> Message: ...

    def list_messages(self, user_id: str, thread_id: str) -> list[Message]: ...

    def get_summary(self, user_id: str, thread_id: str) -> Summary | None: ...

    def save_summary(
        self, user_id: str, thread_id: str, summary: Summary
    ) -> None: ...

    def list_sessions(self, user_id: str) -> list[Session]: ...

    def delete_session(self, user_id: str, thread_id: str) -> None: ...
