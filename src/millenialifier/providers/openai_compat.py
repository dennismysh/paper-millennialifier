"""OpenAI-compatible provider — covers OpenAI, Groq, OpenRouter, and Ollama."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from millenialifier.providers.base import LLMProvider, Message


class OpenAICompatProvider(LLMProvider):
    """Generic provider for any OpenAI-compatible API."""

    def __init__(
        self,
        name: str,
        default_model: str,
        base_url: str | None = None,
        api_key_env: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from openai import AsyncOpenAI

        self.name = name
        self.default_model = default_model

        resolved_key = api_key or (os.environ.get(api_key_env) if api_key_env else None)

        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=resolved_key or "not-needed",
        )
        self._api_key_env = api_key_env

    async def complete(
        self,
        system: str,
        messages: list[Message],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        chat_messages = [{"role": "system", "content": system}]
        chat_messages.extend({"role": m.role, "content": m.content} for m in messages)

        resp = await self._client.chat.completions.create(
            model=self.get_model(model),
            max_tokens=max_tokens,
            messages=chat_messages,
        )
        return resp.choices[0].message.content

    async def stream(
        self,
        system: str,
        messages: list[Message],
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        chat_messages = [{"role": "system", "content": system}]
        chat_messages.extend({"role": m.role, "content": m.content} for m in messages)

        stream = await self._client.chat.completions.create(
            model=self.get_model(model),
            max_tokens=max_tokens,
            messages=chat_messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def is_configured(self) -> bool:
        if not self._api_key_env:
            return True  # Ollama doesn't need a key
        return bool(os.environ.get(self._api_key_env))


# ── Pre-configured provider factories ──────────────────────────────────────


def openai_provider() -> OpenAICompatProvider:
    """OpenAI (GPT-4o, etc.)"""
    return OpenAICompatProvider(
        name="openai",
        default_model="gpt-4o",
        api_key_env="OPENAI_API_KEY",
    )


def groq_provider() -> OpenAICompatProvider:
    """Groq — fast inference, free tier (Llama, Mixtral)."""
    return OpenAICompatProvider(
        name="groq",
        default_model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
    )


def openrouter_provider() -> OpenAICompatProvider:
    """OpenRouter — model aggregator with free options."""
    return OpenAICompatProvider(
        name="openrouter",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
    )


def ollama_provider() -> OpenAICompatProvider:
    """Ollama — local models, completely free."""
    return OpenAICompatProvider(
        name="ollama",
        default_model="llama3.1",
        base_url="http://localhost:11434/v1",
        api_key_env=None,
    )
