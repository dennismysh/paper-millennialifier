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
    api_key_env: str | list[str] | None  # None means no key needed


PROVIDER_INFO: dict[str, ProviderInfo] = {
    "gemini": ProviderInfo(
        name="gemini",
        description="Google Gemini",
        default_model="gemini-2.0-flash",
        free=True,
        api_key_env=["GOOGLE_API_KEY", "GEMINI_API_KEY"],
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

    env_vars = info.api_key_env if isinstance(info.api_key_env, list) else [info.api_key_env]
    if not any(os.environ.get(var) for var in env_vars):
        names = " or ".join(env_vars)
        raise ProviderNotConfiguredError(
            f"Provider '{info.name}' requires the {names} environment variable, "
            f"but it is not set. Please set it before using this provider."
        )


def get_provider(name: str = "gemini") -> LLMProvider:
    """Instantiate the Gemini provider.

    Raises ``ProviderNotConfiguredError`` if the required API key isn't set,
    or ``ImportError`` if the required SDK isn't installed.
    """
    check_provider_configured(name)

    if name == "gemini":
        try:
            from millennialifier.providers.google import GeminiProvider
            return GeminiProvider()
        except ImportError:
            raise ImportError(
                "Google GenAI SDK not installed. Run: pip install paper-millennialifier[gemini]"
            )

    raise ValueError(
        f"Unknown provider '{name}'. Only 'gemini' is supported."
    )


def list_providers() -> list[ProviderInfo]:
    """Return all registered providers."""
    return list(PROVIDER_INFO.values())
