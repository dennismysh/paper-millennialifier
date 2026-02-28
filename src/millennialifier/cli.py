"""CLI interface for the Paper Millennial-ifier."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from millennialifier.models import ToneLevel
from millennialifier.parsers.fetcher import fetch_paper
from millennialifier.translator import translate_paper

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
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to a markdown file instead of stdout.",
    ),
) -> None:
    """Translate a research paper into millennial speak."""
    tone_level = ToneLevel(tone)

    console.print(
        Panel(
            f"[bold]Paper Millennial-ifier[/bold]\n"
            f"Source: {source}\n"
            f"Model: gemini-2.0-flash\n"
            f"Tone: {_tone_name(tone_level)} ({tone}/5)",
            border_style="cyan",
        )
    )

    asyncio.run(_run_translation(source, tone_level, output))


async def _run_translation(
    source: str,
    tone: ToneLevel,
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
