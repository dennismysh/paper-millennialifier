"""Translation engine — sends paper sections to an LLM for millennial-ification."""

from __future__ import annotations

from collections.abc import AsyncIterator

from millennialifier.models import Paper, Section, ToneLevel
from millennialifier.prompts import build_section_prompt, build_system_prompt
from millennialifier.providers import LLMProvider, Message, get_provider


DEFAULT_PROVIDER = "gemini"


def _resolve_provider(
    provider: LLMProvider | None = None,
    provider_name: str | None = None,
) -> LLMProvider:
    """Get a provider instance — use the one passed in, or create from name."""
    if provider is not None:
        return provider
    return get_provider(provider_name or DEFAULT_PROVIDER)


async def translate_section(
    section: Section,
    tone: ToneLevel = ToneLevel.BALANCED,
    model: str | None = None,
    provider: LLMProvider | None = None,
    provider_name: str | None = None,
) -> str:
    """Translate a single paper section.

    Args:
        section: The section to translate.
        tone: Millennial intensity level (1-5).
        model: Model ID override (uses provider default if None).
        provider: A pre-configured LLMProvider instance.
        provider_name: Provider name to instantiate (ignored if provider given).

    Returns:
        The translated section text.
    """
    llm = _resolve_provider(provider, provider_name)
    system_prompt = build_system_prompt(tone)
    user_prompt = build_section_prompt(section.heading, section.content)

    return await llm.complete(
        system=system_prompt,
        messages=[Message(role="user", content=user_prompt)],
        model=model,
    )


async def translate_section_stream(
    section: Section,
    tone: ToneLevel = ToneLevel.BALANCED,
    model: str | None = None,
    provider: LLMProvider | None = None,
    provider_name: str | None = None,
) -> AsyncIterator[str]:
    """Translate a single section with streaming output.

    Yields text chunks as they arrive.
    """
    llm = _resolve_provider(provider, provider_name)
    system_prompt = build_system_prompt(tone)
    user_prompt = build_section_prompt(section.heading, section.content)

    async for chunk in llm.stream(
        system=system_prompt,
        messages=[Message(role="user", content=user_prompt)],
        model=model,
    ):
        yield chunk


async def translate_paper(
    paper: Paper,
    tone: ToneLevel = ToneLevel.BALANCED,
    model: str | None = None,
    provider_name: str | None = None,
    on_section_start: callable | None = None,
    on_section_done: callable | None = None,
) -> Paper:
    """Translate all sections of a paper.

    Processes sections sequentially to provide clear progress feedback.

    Args:
        paper: The parsed paper.
        tone: Millennial intensity level.
        model: Model ID override.
        provider_name: Which LLM provider to use.
        on_section_start: Callback(section_index, heading) called before each section.
        on_section_done: Callback(section_index, heading) called after each section.

    Returns:
        The same Paper object with translated fields populated.
    """
    llm = _resolve_provider(provider_name=provider_name)
    all_sections = paper.all_sections()

    for i, section in enumerate(all_sections):
        if on_section_start:
            on_section_start(i, section.heading)

        translated = await translate_section(
            section, tone=tone, model=model, provider=llm
        )
        section.translated = translated

        if on_section_done:
            on_section_done(i, section.heading)

    # Write translations back to paper
    if paper.abstract and all_sections:
        # First section was the abstract
        paper.abstract = all_sections[0].translated or paper.abstract
        paper.sections = all_sections[1:]
    else:
        paper.sections = all_sections

    return paper
