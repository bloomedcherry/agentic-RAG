"""Session context window and summary coordination."""

from __future__ import annotations

from typing import Any

from enterprise_agent.memory.base import MemoryStore
from enterprise_agent.memory.models import Message, Summary
from enterprise_agent.memory.summarizer import MemorySummarizer


class MemoryManager:
    def __init__(
        self,
        store: MemoryStore,
        *,
        summarizer: MemorySummarizer | None = None,
        max_recent_turns: int = 10,
        max_context_tokens: int = 2000,
    ) -> None:
        self.store = store
        self.summarizer = summarizer or MemorySummarizer()
        self.max_recent_turns = max_recent_turns
        self.max_context_tokens = max_context_tokens

    def load_context(self, user_id: str, thread_id: str) -> dict[str, Any]:
        summary = self.store.get_summary(user_id, thread_id)
        covered_until = summary.covered_until_seq if summary else 0
        unsummarized = [
            message
            for message in self.store.list_messages(user_id, thread_id)
            if (message.seq or 0) > covered_until
        ]
        recent = self._recent_window(unsummarized)
        recent_start = recent[0].seq if recent else None
        needs_summary = bool(
            unsummarized
            and (
                len(recent) < len(unsummarized)
                or sum(message.token_count for message in unsummarized)
                > self.max_context_tokens
            )
        )
        return {
            "summary": summary.content if summary else None,
            "summary_version": summary.version if summary else 0,
            "covered_until_seq": covered_until,
            "recent_messages": recent,
            "recent_start_seq": recent_start,
            "total_tokens": sum(message.token_count for message in recent),
            "estimated": any(message.estimated for message in recent),
            "needs_summary": needs_summary,
        }

    def summarize_if_needed(
        self,
        user_id: str,
        thread_id: str,
        context: dict[str, Any] | None = None,
    ) -> Summary | None:
        context = context or self.load_context(user_id, thread_id)
        if not context["needs_summary"]:
            return None
        recent_start = context.get("recent_start_seq")
        covered_until = int(context.get("covered_until_seq") or 0)
        candidates = [
            message
            for message in self.store.list_messages(user_id, thread_id)
            if (message.seq or 0) > covered_until
            and (recent_start is None or (message.seq or 0) < recent_start)
        ]
        if not candidates:
            return None
        content = self.summarizer.summarize(context.get("summary"), candidates)
        if content is None:
            return None
        summary = Summary(
            version=int(context.get("summary_version") or 0) + 1,
            covered_until_seq=int(candidates[-1].seq or covered_until),
            content=content,
            model=self.summarizer.model,
        )
        self.store.save_summary(user_id, thread_id, summary)
        return summary

    def append_exchange(
        self,
        user_id: str,
        thread_id: str,
        query: str,
        answer: str,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> None:
        self.store.append_message(
            user_id,
            thread_id,
            Message(
                role="user",
                content=query,
                token_count=prompt_tokens or estimate_tokens(query),
                estimated=prompt_tokens is None,
            ),
        )
        self.store.append_message(
            user_id,
            thread_id,
            Message(
                role="assistant",
                content=answer,
                token_count=completion_tokens or estimate_tokens(answer),
                estimated=completion_tokens is None,
            ),
        )
        self.summarize_if_needed(user_id, thread_id)

    def _recent_window(self, messages: list[Message]) -> list[Message]:
        selected: list[Message] = []
        token_total = 0
        max_messages = self.max_recent_turns * 2
        for message in reversed(messages):
            if len(selected) >= max_messages:
                break
            if selected and token_total + message.token_count > self.max_context_tokens:
                break
            if not selected and message.token_count > self.max_context_tokens:
                continue
            selected.append(message)
            token_total += message.token_count
        return list(reversed(selected))


def estimate_tokens(text: str) -> int:
    compact = " ".join(text.split())
    if not compact:
        return 0
    return max(1, (len(compact) + 3) // 4)
