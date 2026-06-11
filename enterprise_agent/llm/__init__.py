"""Framework-neutral LLM contracts and clients."""

from enterprise_agent.llm.base import BaseLLMClient, LLMRequest, LLMResponse
from enterprise_agent.llm.client import OpenAICompatibleClient
from enterprise_agent.llm.fake import FakeLLMClient

__all__ = [
    "BaseLLMClient",
    "FakeLLMClient",
    "LLMRequest",
    "LLMResponse",
    "OpenAICompatibleClient",
]
