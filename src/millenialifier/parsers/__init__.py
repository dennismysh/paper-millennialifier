"""Paper parsers for PDF, HTML, and URL sources."""

from millenialifier.parsers.pdf import PdfParser
from millenialifier.parsers.html import HtmlParser
from millenialifier.parsers.fetcher import fetch_paper

__all__ = ["PdfParser", "HtmlParser", "fetch_paper"]
