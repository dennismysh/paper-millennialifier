"""LLM provider registry.

Providers are loaded lazily — only the SDK you actually use needs to be installed.
"""

from __future__ import annotations

from dataclasses import dataclass

from millennialifier.providers.base import LLMProvider, Message

__all__ = [
    "LLMProvider",
    "Message",
    "get_provider",
    "check_provider_configured",
    "list_providers",
    "PROVIDER_INFO",
]


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


class ProviderNotConfiguredError(Exception):
    """Raised when a provider's API key is not set."""


def check_provider_configured(name: str) -> None:
    """Raise ``ProviderNotConfiguredError`` if the provider's API key isn't set.

    Call this *before* instantiating the provider so the user gets a clear
    message instead of a cryptic SDK auth failure.
    """
    info = PROVIDER_INFO.get(name)
    if info is None:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {', '.join(PROVIDER_INFO.keys())}"
        )
    if info.api_key_env is None:
        return  # Ollama — no key needed
    import os

    if not os.environ.get(info.api_key_env):
        raise ProviderNotConfiguredError(
            f"Provider '{info.name}' requires the {info.api_key_env} environment variable, "
            f"but it is not set. Please set it before using this provider."
        )


def get_provider(name: str) -> LLMProvider:
    """Instantiate a provider by name.

    Raises ``ProviderNotConfiguredError`` if the required API key isn't set,
    or ``ImportError`` if the required SDK isn't installed.
    """
    check_provider_configured(name)

    if name == "claude":
        try:
            from millennialifier.providers.anthropic import AnthropicProvider
            return AnthropicProvider()
        except ImportError:
            raise ImportError(
                "Anthropic SDK not installed. Run: pip install paper-millennialifier[claude]"
            )

    if name == "openai":
        try:
            from millennialifier.providers.openai_compat import openai_provider
            return openai_provider()
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed. Run: pip install paper-millennialifier[openai]"
            )

    if name == "gemini":
        try:
            from millennialifier.providers.google import GeminiProvider
            return GeminiProvider()
        except ImportError:
            raise ImportError(
                "Google GenAI SDK not installed. Run: pip install paper-millennialifier[gemini]"
            )

    if name == "groq":
        try:
            from millennialifier.providers.openai_compat import groq_provider
            return groq_provider()
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed (used for Groq). Run: pip install paper-millennialifier[openai]"
            )

    if name == "openrouter":
        try:
            from millennialifier.providers.openai_compat import openrouter_provider
            return openrouter_provider()
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed (used for OpenRouter). Run: pip install paper-millennialifier[openai]"
            )

    if name == "ollama":
        try:
            from millennialifier.providers.openai_compat import ollama_provider
            return ollama_provider()
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed (used for Ollama). Run: pip install paper-millennialifier[openai]"
            )

    raise ValueError(
        f"Unknown provider '{name}'. Available: {', '.join(PROVIDER_INFO.keys())}"
    )


def list_providers() -> list[ProviderInfo]:
    """Return all registered providers."""
    return list(PROVIDER_INFO.values())
