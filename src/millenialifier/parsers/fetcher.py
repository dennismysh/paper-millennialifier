"""Fetch papers from URLs, with special handling for arXiv."""

from __future__ import annotations

import re
from pathlib import Path

import httpx

from millenialifier.models import Paper
from millenialifier.parsers.html import HtmlParser
from millenialifier.parsers.pdf import PdfParser

# arXiv abstract page: https://arxiv.org/abs/2301.12345
_ARXIV_ABS_RE = re.compile(r"arxiv\.org/abs/([\w.]+)")
# arXiv PDF page: https://arxiv.org/pdf/2301.12345
_ARXIV_PDF_RE = re.compile(r"arxiv\.org/pdf/([\w.]+)")


def _arxiv_id_from_url(url: str) -> str | None:
    """Extract arXiv paper ID from a URL."""
    for pattern in (_ARXIV_ABS_RE, _ARXIV_PDF_RE):
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def _arxiv_html_url(arxiv_id: str) -> str:
    """Build the arXiv HTML page URL."""
    return f"https://arxiv.org/html/{arxiv_id}"


def _arxiv_pdf_url(arxiv_id: str) -> str:
    """Build the arXiv PDF URL."""
    return f"https://arxiv.org/pdf/{arxiv_id}"


async def fetch_paper(
    source: str,
    prefer_html: bool = True,
) -> Paper:
    """Fetch and parse a paper from a URL or local file path.

    For arXiv URLs, attempts HTML first (cleaner parsing), falls back to PDF.

    Args:
        source: A URL or local file path.
        prefer_html: If True and source is arXiv, try HTML before PDF.

    Returns:
        A parsed Paper object.
    """
    path = Path(source)
    if path.exists():
        return _parse_local(path)

    return await _fetch_remote(source, prefer_html)


def _parse_local(path: Path) -> Paper:
    """Parse a local file."""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        paper = PdfParser().parse(path)
    elif suffix in (".html", ".htm"):
        paper = HtmlParser().parse(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return paper


async def _fetch_remote(url: str, prefer_html: bool) -> Paper:
    """Fetch and parse a remote paper."""
    arxiv_id = _arxiv_id_from_url(url)

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        if arxiv_id and prefer_html:
            # Try arXiv HTML first — it parses much cleaner
            html_url = _arxiv_html_url(arxiv_id)
            try:
                resp = await client.get(html_url)
                if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                    paper = HtmlParser().parse_string(resp.text)
                    paper.source_url = url
                    return paper
            except httpx.HTTPError:
                pass  # Fall through to PDF

            # Fall back to PDF
            pdf_url = _arxiv_pdf_url(arxiv_id)
            resp = await client.get(pdf_url)
            resp.raise_for_status()
            paper = PdfParser().parse_bytes(resp.content)
            paper.source_url = url
            return paper

        # Non-arXiv URL: guess format from content-type
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")

        if "pdf" in content_type:
            paper = PdfParser().parse_bytes(resp.content)
        else:
            paper = HtmlParser().parse_string(resp.text)

        paper.source_url = url
        return paper
