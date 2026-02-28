"""CLI interface for the Paper Millennial-ifier."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from millenialifier.models import ToneLevel
from millenialifier.parsers.fetcher import fetch_paper
from millenialifier.providers import PROVIDER_INFO
from millenialifier.translator import translate_paper

app = typer.Typer(
    name="millenialify",
    help="Translate research papers into millennial speak.",
    no_args_is_help=True,
)

console = Console()


def _tone_name(tone: ToneLevel) -> str:
    return {
        ToneLevel.LIGHT: "Light",
        ToneLevel.MODERATE: "Moderate",
        ToneLevel.BALANCED: "Balanced",
        ToneLevel.HEAVY: "Heavy",
        ToneLevel.UNHINGED: "UNHINGED",
    }[tone]


@app.command()
def translate(
    source: str = typer.Argument(
        help="URL or local file path to a research paper (PDF or HTML).",
    ),
    tone: int = typer.Option(
        3,
        "--tone",
        "-t",
        min=1,
        max=5,
        help="Millennial intensity: 1=light, 2=moderate, 3=balanced, 4=heavy, 5=unhinged.",
    ),
    provider: str = typer.Option(
        "claude",
        "--provider",
        "-p",
        help="LLM provider: claude, openai, gemini, groq, openrouter, ollama.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Model ID override (uses provider default if omitted).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to a markdown file instead of stdout.",
    ),
) -> None:
    """Translate a research paper into millennial speak."""
    tone_level = ToneLevel(tone)

    # Resolve display model name
    info = PROVIDER_INFO.get(provider)
    display_model = model or (info.default_model if info else "?")

    console.print(
        Panel(
            f"[bold]Paper Millennial-ifier[/bold]\n"
            f"Source: {source}\n"
            f"Provider: {provider} ({display_model})\n"
            f"Tone: {_tone_name(tone_level)} ({tone}/5)",
            border_style="cyan",
        )
    )

    asyncio.run(_run_translation(source, tone_level, provider, model, output))


async def _run_translation(
    source: str,
    tone: ToneLevel,
    provider_name: str,
    model: str | None,
    output: Path | None,
) -> None:
    # Parse
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching and parsing paper...", total=None)
        paper = await fetch_paper(source)
        progress.update(task, description="[green]Paper parsed!")

    console.print(f"\n[bold]{paper.title}[/bold]")
    if paper.authors:
        console.print(f"[dim]{', '.join(paper.authors)}[/dim]")

    sections = paper.all_sections()
    console.print(f"Found [cyan]{len(sections)}[/cyan] sections to translate.\n")

    # Translate section by section with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Translating...", total=len(sections))

        def on_start(i: int, heading: str) -> None:
            progress.update(task, description=f"Translating: {heading}")

        def on_done(i: int, heading: str) -> None:
            progress.advance(task)

        paper = await translate_paper(
            paper,
            tone=tone,
            model=model,
            provider_name=provider_name,
            on_section_start=on_start,
            on_section_done=on_done,
        )

    # Build output
    lines: list[str] = []
    lines.append(f"# {paper.title}\n")

    if paper.abstract:
        lines.append("## Abstract\n")
        lines.append(paper.abstract + "\n")

    for section in paper.sections:
        text = section.translated or section.content
        lines.append(f"## {section.heading}\n")
        lines.append(text + "\n")

    result = "\n".join(lines)

    if output:
        output.write_text(result, encoding="utf-8")
        console.print(f"\n[green]Saved to {output}[/green]")
    else:
        console.print()
        console.print(Markdown(result))


@app.command()
def providers() -> None:
    """List available LLM providers and their configuration status."""
    table = Table(title="Available Providers")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description")
    table.add_column("Default Model", style="dim")
    table.add_column("Free?", justify="center")
    table.add_column("Status", justify="center")

    for info in PROVIDER_INFO.values():
        # Check if configured
        if info.api_key_env is None:
            status = "[green]Ready[/green]"
        elif os.environ.get(info.api_key_env):
            status = "[green]Configured[/green]"
        else:
            status = f"[yellow]Set {info.api_key_env}[/yellow]"

        free = "[green]Yes[/green]" if info.free else "[dim]No[/dim]"

        table.add_row(info.name, info.description, info.default_model, free, status)

    console.print(table)
    console.print(
        "\n[dim]Use --provider/-p with the translate command, e.g.:[/dim]"
        "\n  millenialify translate paper.pdf --provider groq"
    )


@app.command()
def tones() -> None:
    """Show all available tone levels with descriptions."""
    descriptions = {
        1: "Light — dinner party explanation, minimal slang",
        2: "Moderate — texting a smart friend, some slang",
        3: "Balanced — PhD podcast host who brunches (default)",
        4: "Heavy — your most dramatic brilliant friend",
        5: "UNHINGED — chaotic group chat dissertation defense",
    }
    console.print("[bold]Available tone levels:[/bold]\n")
    for level, desc in descriptions.items():
        console.print(f"  [cyan]{level}[/cyan]  {desc}")


if __name__ == "__main__":
    app()
