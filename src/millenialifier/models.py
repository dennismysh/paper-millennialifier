"""Data models for paper parsing and translation."""

from dataclasses import dataclass, field
from enum import IntEnum


class ToneLevel(IntEnum):
    """How millennial the output should be. Scale of 1-5."""

    LIGHT = 1       # Casual rewrite, minimal slang
    MODERATE = 2    # Noticeably casual, some slang
    BALANCED = 3    # Default — solid mix of clarity and millennial energy
    HEAVY = 4       # Very casual, lots of slang and references
    UNHINGED = 5    # Full millennial chaos mode


@dataclass
class Section:
    """A single section of a research paper."""

    heading: str
    content: str
    translated: str | None = None


@dataclass
class Paper:
    """A parsed research paper, ready for translation."""

    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    sections: list[Section] = field(default_factory=list)
    source_url: str | None = None
    source_format: str = "unknown"  # "pdf", "html"

    def all_sections(self) -> list[Section]:
        """Return all translatable sections, including abstract."""
        parts = []
        if self.abstract:
            parts.append(Section(heading="Abstract", content=self.abstract))
        parts.extend(self.sections)
        return parts
