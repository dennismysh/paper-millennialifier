"""Abstract base for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str


class LLMProvider(ABC):
    """Interface that all LLM providers must implement."""

    name: str
    default_model: str

    @abstractmethod
    async def complete(
        self,
        system: str,
        messages: list[Message],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Send a prompt and return the full response text."""

    @abstractmethod
    async def stream(
        self,
        system: str,
        messages: list[Message],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Send a prompt and yield response text chunks as they arrive."""

    def get_model(self, model: str | None) -> str:
        """Return the requested model or the provider's default."""
        return model or self.default_model
