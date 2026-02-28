"""Google Gemini provider — generous free tier."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from millenialifier.providers.base import LLMProvider, Message


class GeminiProvider(LLMProvider):
    name = "gemini"
    default_model = "gemini-2.0-flash"

    def __init__(self) -> None:
        from google import genai

        self._client = genai.Client()

    async def complete(
        self,
        system: str,
        messages: list[Message],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        from google.genai import types

        contents = [types.Content(role=m.role, parts=[types.Part(text=m.content)]) for m in messages]

        response = await self._client.aio.models.generate_content(
            model=self.get_model(model),
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text

    async def stream(
        self,
        system: str,
        messages: list[Message],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        from google.genai import types

        contents = [types.Content(role=m.role, parts=[types.Part(text=m.content)]) for m in messages]

        async for chunk in await self._client.aio.models.generate_content_stream(
            model=self.get_model(model),
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
        ):
            if chunk.text:
                yield chunk.text

    @staticmethod
    def is_configured() -> bool:
        return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
