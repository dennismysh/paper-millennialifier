"""FastAPI web app for the Paper Millennial-ifier."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from millenialifier.models import ToneLevel
from millenialifier.parsers.fetcher import fetch_paper
from millenialifier.parsers.html import HtmlParser
from millenialifier.parsers.pdf import PdfParser
from millenialifier.providers import PROVIDER_INFO
from millenialifier.translator import translate_section_stream

_ROOT = Path(__file__).resolve().parent.parent.parent
_TEMPLATES = _ROOT / "templates"
_STATIC = _ROOT / "static"

app = FastAPI(title="Paper Millennial-ifier")
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
templates = Jinja2Templates(directory=str(_TEMPLATES))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/providers")
async def api_providers() -> JSONResponse:
    """Return available providers and their metadata."""
    return JSONResponse([
        {
            "name": info.name,
            "description": info.description,
            "default_model": info.default_model,
            "free": info.free,
        }
        for info in PROVIDER_INFO.values()
    ])


@app.post("/translate")
async def translate(
    request: Request,
    url: str = Form(default=""),
    file: UploadFile | None = None,
    tone: int = Form(default=3),
    provider: str = Form(default="claude"),
    model: str = Form(default=""),
) -> StreamingResponse:
    """Parse a paper and stream the millennial-ified translation back.

    Sends server-sent events (SSE) so the frontend can render progressively.
    """
    tone_level = ToneLevel(tone)
    model_override = model if model else None

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
        # Send paper metadata
        yield _sse(
            "meta",
            {
                "title": paper.title,
                "authors": paper.authors,
                "section_count": len(paper.all_sections()),
            },
        )

        for i, section in enumerate(paper.all_sections()):
            yield _sse("section_start", {"index": i, "heading": section.heading})

            async for chunk in translate_section_stream(
                section,
                tone=tone_level,
                model=model_override,
                provider_name=provider,
            ):
                yield _sse("chunk", {"index": i, "text": chunk})

            yield _sse("section_done", {"index": i, "heading": section.heading})

        yield _sse("done", {})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    """Format a server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _error_stream(message: str):
    yield _sse("error", {"message": message})
