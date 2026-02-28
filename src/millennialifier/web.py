"""FastAPI web app for the Paper Millennial-ifier."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from millennialifier.models import ToneLevel
from millennialifier.parsers.fetcher import fetch_paper
from millennialifier.parsers.html import HtmlParser
from millennialifier.parsers.pdf import PdfParser
from millennialifier.providers import (
    PROVIDER_INFO,
    ProviderNotConfiguredError,
    check_provider_configured,
)
from millennialifier.translator import translate_section_stream

_PROVIDER = "gemini"
_MODEL = "gemini-2.0-flash"

_ROOT = Path(__file__).resolve().parent.parent.parent
_TEMPLATES = _ROOT / "templates"
_STATIC = _ROOT / "static"

app = FastAPI(title="Paper Millennial-ifier")
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
templates = Jinja2Templates(directory=str(_TEMPLATES))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/translate")
async def translate(
    request: Request,
    url: str = Form(default=""),
    file: UploadFile | None = None,
    tone: int = Form(default=3),
) -> StreamingResponse:
    """Parse a paper and stream the millennial-ified translation back.

    Sends server-sent events (SSE) so the frontend can render progressively.
    """
    tone_level = ToneLevel(tone)

    # Validate API key before doing any work
    try:
        check_provider_configured(_PROVIDER)
    except (ProviderNotConfiguredError, ValueError) as exc:
        return StreamingResponse(
            _error_stream(str(exc)),
            media_type="text/event-stream",
        )

    # Parse the paper from URL or uploaded file
    if file and file.filename:
        data = await file.read()
        suffix = Path(file.filename).suffix.lower()
        if suffix == ".pdf":
            paper = PdfParser().parse_bytes(data)
        else:
            paper = HtmlParser().parse_string(data.decode("utf-8", errors="replace"))
    elif url:
        paper = await fetch_paper(url)
    else:
        return StreamingResponse(
            _error_stream("Please provide a URL or upload a file."),
            media_type="text/event-stream",
        )

    async def event_stream():
        # Send paper metadata + provider info
        yield _sse(
            "meta",
            {
                "title": paper.title,
                "authors": paper.authors,
                "section_count": len(paper.all_sections()),
                "provider": _PROVIDER,
                "model": _MODEL,
            },
        )

        try:
            for i, section in enumerate(paper.all_sections()):
                yield _sse("section_start", {"index": i, "heading": section.heading})

                async for chunk in translate_section_stream(
                    section,
                    tone=tone_level,
                    provider_name=_PROVIDER,
                ):
                    yield _sse("chunk", {"index": i, "text": chunk})

                yield _sse("section_done", {"index": i, "heading": section.heading})
        except Exception as exc:
            yield _sse("error", {"message": _friendly_error(_PROVIDER, exc)})
            return

        yield _sse("done", {})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    """Format a server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _error_stream(message: str):
    yield _sse("error", {"message": message})


def _friendly_error(provider_name: str, exc: Exception) -> str:
    """Turn a raw SDK exception into a human-readable message."""
    raw = str(exc).lower()
    info = PROVIDER_INFO.get(provider_name)
    if info and info.api_key_env:
        env_names = info.api_key_env if isinstance(info.api_key_env, list) else [info.api_key_env]
        env_hint = f" ({' or '.join(env_names)})"
    else:
        env_hint = ""

    if "api key not valid" in raw or "invalid api key" in raw or "unauthorized" in raw or "401" in raw:
        return (
            f"Your {provider_name} API key{env_hint} is invalid. "
            "Please double-check the key and try again."
        )
    if "quota" in raw or "rate limit" in raw or "429" in raw:
        return (
            f"Rate limit or quota exceeded for {provider_name}. "
            "Please wait a moment and try again."
        )
    if "not found" in raw or "404" in raw:
        return (
            f"The requested model was not found on {provider_name}. "
            "Please check the model name or leave it blank for the default."
        )
    # Fall back to the raw message, but strip the SDK prefix noise
    return f"Error from {provider_name}: {exc}"
