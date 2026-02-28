"""PDF parser for research papers using PyMuPDF."""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from millennialifier.models import Paper, Section


# Common section headings in research papers
_HEADING_PATTERNS = [
    r"^(?:\d+\.?\s+)?(abstract)$",
    r"^(?:\d+\.?\s+)?(introduction)$",
    r"^(?:\d+\.?\s+)?(related\s+work)$",
    r"^(?:\d+\.?\s+)?(background)$",
    r"^(?:\d+\.?\s+)?(method(?:ology|s)?)$",
    r"^(?:\d+\.?\s+)?(approach)$",
    r"^(?:\d+\.?\s+)?(experiment(?:s|al\s+(?:setup|results))?)$",
    r"^(?:\d+\.?\s+)?(results?)$",
    r"^(?:\d+\.?\s+)?(evaluation)$",
    r"^(?:\d+\.?\s+)?(discussion)$",
    r"^(?:\d+\.?\s+)?(conclusion(?:s)?)$",
    r"^(?:\d+\.?\s+)?(future\s+work)$",
    r"^(?:\d+\.?\s+)?(acknowledge?ments?)$",
    r"^(?:\d+\.?\s+)?(references?)$",
    r"^(?:\d+\.?\s+)?(appendi(?:x|ces))$",
    # Generic numbered section: "3. Something Something"
    r"^(\d+\.?\s+\S.{2,60})$",
]

_HEADING_RE = [re.compile(p, re.IGNORECASE) for p in _HEADING_PATTERNS]


def _is_heading(line: str) -> bool:
    """Check if a line looks like a section heading."""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    return any(r.match(stripped) for r in _HEADING_RE)


def _clean_heading(line: str) -> str:
    """Normalize a heading string."""
    stripped = line.strip()
    # Remove leading numbers like "1." or "2.1"
    cleaned = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", stripped)
    return cleaned.title() if cleaned else stripped


class PdfParser:
    """Extract structured sections from a research paper PDF."""

    def parse(self, source: str | Path) -> Paper:
        """Parse a PDF file into a Paper object.

        Args:
            source: Path to a PDF file.
        """
        path = Path(source)
        doc = pymupdf.open(str(path))

        # Extract full text page by page
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        return self._structure_text(full_text, source_format="pdf")

    def parse_bytes(self, data: bytes) -> Paper:
        """Parse PDF bytes into a Paper object."""
        doc = pymupdf.open(stream=data, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        return self._structure_text(full_text, source_format="pdf")

    def _structure_text(self, text: str, source_format: str) -> Paper:
        """Split raw text into structured sections."""
        lines = text.split("\n")

        title = ""
        authors: list[str] = []
        abstract = ""
        sections: list[Section] = []
        current_heading: str | None = None
        current_lines: list[str] = []

        # First non-empty line is likely the title
        for line in lines:
            if line.strip():
                title = line.strip()
                break

        in_body = False
        for line in lines:
            if _is_heading(line):
                # Save previous section
                if current_heading is not None:
                    body = "\n".join(current_lines).strip()
                    if current_heading.lower() == "abstract":
                        abstract = body
                    else:
                        sections.append(Section(heading=current_heading, content=body))

                current_heading = _clean_heading(line)
                current_lines = []
                in_body = True
            elif in_body:
                current_lines.append(line)

        # Don't forget the last section
        if current_heading is not None:
            body = "\n".join(current_lines).strip()
            if current_heading.lower() == "abstract":
                abstract = body
            else:
                sections.append(Section(heading=current_heading, content=body))

        # If no sections found, treat the whole text as one section
        if not sections and not abstract:
            sections.append(Section(heading="Full Paper", content=text.strip()))

        return Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
            source_format=source_format,
        )
