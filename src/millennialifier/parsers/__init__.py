"""Paper parsers for PDF, HTML, and URL sources."""

from millennialifier.parsers.pdf import PdfParser
from millennialifier.parsers.html import HtmlParser
from millennialifier.parsers.fetcher import fetch_paper

__all__ = ["PdfParser", "HtmlParser", "fetch_paper"]
