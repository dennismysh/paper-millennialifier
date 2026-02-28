"""Anthropic (Claude) provider."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from millennialifier.providers.base import LLMProvider, Message


class AnthropicProvider(LLMProvider):
    name = "claude"
    default_model = "claude-sonnet-4-20250514"

    def __init__(self) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic()

    async def complete(
        self,
        system: str,
        messages: list[Message],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        msg = await self._client.messages.create(
            model=self.get_model(model),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return msg.content[0].text

    async def stream(
        self,
        system: str,
        messages: list[Message],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self.get_model(model),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        ) as s:
            async for text in s.text_stream:
                yield text

    @staticmethod
    def is_configured() -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
