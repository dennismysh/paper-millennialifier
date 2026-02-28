"""HTML parser for research papers (arXiv HTML, journals, etc.)."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup, Tag

from millennialifier.models import Paper, Section


# Tags that typically contain section headings
_HEADING_TAGS = {"h1", "h2", "h3", "h4"}

# Sections to skip entirely
_SKIP_HEADINGS = {"references", "bibliography", "acknowledgements", "acknowledgments"}


class HtmlParser:
    """Extract structured sections from an HTML research paper."""

    def parse(self, source: str | Path) -> Paper:
        """Parse an HTML file into a Paper object.

        Args:
            source: Path to an HTML file.
        """
        path = Path(source)
        html = path.read_text(encoding="utf-8")
        return self.parse_string(html)

    def parse_string(self, html: str) -> Paper:
        """Parse an HTML string into a Paper object."""
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        authors = self._extract_authors(soup)
        abstract = self._extract_abstract(soup)
        sections = self._extract_sections(soup)

        return Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
            source_format="html",
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Pull the paper title."""
        # arXiv HTML uses <h1 class="ltx_title">
        for cls in ("ltx_title", "document-title", "title"):
            tag = soup.find(class_=cls)
            if tag:
                return tag.get_text(strip=True)

        # Fallback to <title> tag
        if soup.title:
            return soup.title.get_text(strip=True)

        return "Untitled"

    def _extract_authors(self, soup: BeautifulSoup) -> list[str]:
        """Pull author names."""
        authors: list[str] = []

        # arXiv HTML uses <span class="ltx_personname">
        for tag in soup.find_all(class_="ltx_personname"):
            name = tag.get_text(strip=True)
            if name:
                authors.append(name)

        if not authors:
            # Generic meta tag fallback
            for meta in soup.find_all("meta", attrs={"name": "author"}):
                content = meta.get("content", "")
                if content:
                    authors.append(content)

        return authors

    def _extract_abstract(self, soup: BeautifulSoup) -> str:
        """Pull the abstract text."""
        # arXiv HTML: <div class="ltx_abstract">
        for cls in ("ltx_abstract", "abstract"):
            tag = soup.find(class_=cls)
            if tag:
                # Remove the "Abstract" heading if present
                heading = tag.find(class_="ltx_title")
                if heading:
                    heading.decompose()
                return tag.get_text(strip=True)

        return ""

    def _extract_sections(self, soup: BeautifulSoup) -> list[Section]:
        """Extract paper sections by finding headings and their content."""
        sections: list[Section] = []

        # arXiv HTML wraps sections in <section class="ltx_section">
        ltx_sections = soup.find_all(class_="ltx_section")
        if ltx_sections:
            return self._parse_ltx_sections(ltx_sections)

        # Generic approach: walk heading tags
        return self._parse_generic_sections(soup)

    def _parse_ltx_sections(self, ltx_sections: list[Tag]) -> list[Section]:
        """Parse arXiv-style <section class='ltx_section'> elements."""
        sections: list[Section] = []

        for sec in ltx_sections:
            heading_tag = sec.find(class_="ltx_title")
            heading = heading_tag.get_text(strip=True) if heading_tag else "Untitled Section"

            if heading.lower() in _SKIP_HEADINGS:
                continue

            # Remove the heading from the section content
            if heading_tag:
                heading_tag.decompose()

            content = sec.get_text(separator="\n", strip=True)
            if content:
                sections.append(Section(heading=heading, content=content))

        return sections

    def _parse_generic_sections(self, soup: BeautifulSoup) -> list[Section]:
        """Fallback: walk the DOM looking for heading tags."""
        sections: list[Section] = []
        current_heading: str | None = None
        current_parts: list[str] = []

        body = soup.find("body") or soup
        for element in body.children:
            if not isinstance(element, Tag):
                continue

            if element.name in _HEADING_TAGS:
                # Save previous section
                if current_heading is not None:
                    content = "\n".join(current_parts).strip()
                    if content and current_heading.lower() not in _SKIP_HEADINGS:
                        sections.append(Section(heading=current_heading, content=content))
                current_heading = element.get_text(strip=True)
                current_parts = []
            elif current_heading is not None:
                text = element.get_text(separator="\n", strip=True)
                if text:
                    current_parts.append(text)

        # Last section
        if current_heading is not None:
            content = "\n".join(current_parts).strip()
            if content and current_heading.lower() not in _SKIP_HEADINGS:
                sections.append(Section(heading=current_heading, content=content))

        # If nothing found, grab all paragraph text as one section
        if not sections:
            all_text = soup.get_text(separator="\n", strip=True)
            if all_text:
                sections.append(Section(heading="Full Paper", content=all_text))

        return sections
