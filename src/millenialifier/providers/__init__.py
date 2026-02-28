"""LLM provider registry.

Providers are loaded lazily — only the SDK you actually use needs to be installed.
"""

from __future__ import annotations

from dataclasses import dataclass

from millenialifier.providers.base import LLMProvider, Message

__all__ = ["LLMProvider", "Message", "get_provider", "list_providers", "PROVIDER_INFO"]


@dataclass
class ProviderInfo:
    """Metadata about a provider (available before instantiation)."""

    name: str
    description: str
    default_model: str
    free: bool
    api_key_env: str | None  # None means no key needed


PROVIDER_INFO: dict[str, ProviderInfo] = {
    "claude": ProviderInfo(
        name="claude",
        description="Anthropic Claude",
        default_model="claude-sonnet-4-20250514",
        free=False,
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "openai": ProviderInfo(
        name="openai",
        description="OpenAI (GPT-4o, etc.)",
        default_model="gpt-4o",
        free=False,
        api_key_env="OPENAI_API_KEY",
    ),
    "gemini": ProviderInfo(
        name="gemini",
        description="Google Gemini — generous free tier",
        default_model="gemini-2.0-flash",
        free=True,
        api_key_env="GOOGLE_API_KEY",
    ),
    "groq": ProviderInfo(
        name="groq",
        description="Groq — fast inference, free tier (Llama 3.3, Mixtral)",
        default_model="llama-3.3-70b-versatile",
        free=True,
        api_key_env="GROQ_API_KEY",
    ),
    "openrouter": ProviderInfo(
        name="openrouter",
        description="OpenRouter — model aggregator with free options",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        free=True,
        api_key_env="OPENROUTER_API_KEY",
    ),
    "ollama": ProviderInfo(
        name="ollama",
        description="Ollama — local models, completely free, no API key",
        default_model="llama3.1",
        free=True,
        api_key_env=None,
    ),
}


def get_provider(name: str) -> LLMProvider:
    """Instantiate a provider by name.

    Raises ImportError with a helpful message if the required SDK isn't installed.
    """
    if name == "claude":
        try:
            from millenialifier.providers.anthropic import AnthropicProvider
            return AnthropicProvider()
        except ImportError:
            raise ImportError(
                "Anthropic SDK not installed. Run: pip install paper-millenialifier[claude]"
            )

    if name == "openai":
        try:
            from millenialifier.providers.openai_compat import openai_provider
            return openai_provider()
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed. Run: pip install paper-millenialifier[openai]"
            )

    if name == "gemini":
        try:
            from millenialifier.providers.google import GeminiProvider
            return GeminiProvider()
        except ImportError:
            raise ImportError(
                "Google GenAI SDK not installed. Run: pip install paper-millenialifier[gemini]"
            )

    if name == "groq":
        try:
            from millenialifier.providers.openai_compat import groq_provider
            return groq_provider()
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed (used for Groq). Run: pip install paper-millenialifier[openai]"
            )

    if name == "openrouter":
        try:
            from millenialifier.providers.openai_compat import openrouter_provider
            return openrouter_provider()
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed (used for OpenRouter). Run: pip install paper-millenialifier[openai]"
            )

    if name == "ollama":
        try:
            from millenialifier.providers.openai_compat import ollama_provider
            return ollama_provider()
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed (used for Ollama). Run: pip install paper-millenialifier[openai]"
            )

    raise ValueError(
        f"Unknown provider '{name}'. Available: {', '.join(PROVIDER_INFO.keys())}"
    )


def list_providers() -> list[ProviderInfo]:
    """Return all registered providers."""
    return list(PROVIDER_INFO.values())
