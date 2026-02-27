"""Translation engine — sends paper sections to Claude for millennial-ification."""

from __future__ import annotations

from collections.abc import AsyncIterator

import anthropic

from millenialifier.models import Paper, Section, ToneLevel
from millenialifier.prompts import build_section_prompt, build_system_prompt

DEFAULT_MODEL = "claude-sonnet-4-20250514"


async def translate_section(
    section: Section,
    tone: ToneLevel = ToneLevel.BALANCED,
    model: str = DEFAULT_MODEL,
    client: anthropic.AsyncAnthropic | None = None,
) -> str:
    """Translate a single paper section.

    Args:
        section: The section to translate.
        tone: Millennial intensity level (1-5).
        model: Claude model ID to use.
        client: Optional pre-configured client.

    Returns:
        The translated section text.
    """
    if client is None:
        client = anthropic.AsyncAnthropic()

    system_prompt = build_system_prompt(tone)
    user_prompt = build_section_prompt(section.heading, section.content)

    message = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text


async def translate_section_stream(
    section: Section,
    tone: ToneLevel = ToneLevel.BALANCED,
    model: str = DEFAULT_MODEL,
    client: anthropic.AsyncAnthropic | None = None,
) -> AsyncIterator[str]:
    """Translate a single section with streaming output.

    Yields text chunks as they arrive.
    """
    if client is None:
        client = anthropic.AsyncAnthropic()

    system_prompt = build_system_prompt(tone)
    user_prompt = build_section_prompt(section.heading, section.content)

    async with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def translate_paper(
    paper: Paper,
    tone: ToneLevel = ToneLevel.BALANCED,
    model: str = DEFAULT_MODEL,
    on_section_start: callable | None = None,
    on_section_done: callable | None = None,
) -> Paper:
    """Translate all sections of a paper.

    Processes sections sequentially to provide clear progress feedback.

    Args:
        paper: The parsed paper.
        tone: Millennial intensity level.
        model: Claude model ID.
        on_section_start: Callback(section_index, heading) called before each section.
        on_section_done: Callback(section_index, heading) called after each section.

    Returns:
        The same Paper object with translated fields populated.
    """
    client = anthropic.AsyncAnthropic()
    all_sections = paper.all_sections()

    for i, section in enumerate(all_sections):
        if on_section_start:
            on_section_start(i, section.heading)

        translated = await translate_section(
            section, tone=tone, model=model, client=client
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
