# Paper Millennialifier

Translate dense research papers into millennial speak — casual, relatable language while keeping the science intact.

Feed it an arXiv URL, a local PDF, or an HTML document and get back an accessible rewrite at your chosen level of millennial intensity (from "dinner party explanation" to "chaotic group chat energy").

## Features

- **Multi-format input** — URLs (with special arXiv handling), local PDFs, and HTML files
- **5 tone levels** — from Light ("explaining your research at a dinner party") to UNHINGED ("chaotic group chat dissertation defense")
- **6 LLM providers** — Claude, OpenAI, Gemini, Groq, OpenRouter, and Ollama (local)
- **CLI and web interfaces** — Rich-formatted terminal output or a browser-based UI with real-time streaming
- **Streaming translation** — section-by-section progress with live output
- **Scientifically accurate** — the delivery changes, the facts don't

## Installation

Requires **Python 3.10+**.

```bash
# Basic install
pip install paper-millenialifier

# With a specific LLM provider
pip install paper-millenialifier[claude]
pip install paper-millenialifier[openai]
pip install paper-millenialifier[gemini]

# With all providers
pip install paper-millenialifier[all-providers]

# Free-tier providers only (Gemini + OpenAI-compat providers)
pip install paper-millenialifier[free]
```

For development:

```bash
git clone https://github.com/dennismysh/paper-millenialifier.git
cd paper-millenialifier
pip install -e ".[dev,all-providers]"
```

## Configuration

Set the API key for your chosen provider as an environment variable:

| Provider | Environment Variable | Free Tier |
|------------|------------------------|-----------|
| Claude | `ANTHROPIC_API_KEY` | No |
| OpenAI | `OPENAI_API_KEY` | No |
| Gemini | `GOOGLE_API_KEY` | Yes |
| Groq | `GROQ_API_KEY` | Yes |
| OpenRouter | `OPENROUTER_API_KEY` | Yes |
| Ollama | *(none — runs locally)* | Yes |

## Usage

### CLI

```bash
# Translate an arXiv paper
millenialify translate https://arxiv.org/abs/2301.12345

# Translate a local PDF
millenialify translate paper.pdf

# Crank the tone to maximum
millenialify translate paper.pdf --tone 5

# Use a specific provider and model
millenialify translate paper.pdf --provider gemini --model gemini-2.0-flash

# Save output to a file
millenialify translate paper.pdf --output translated.md

# List available providers and their status
millenialify providers

# Show tone level descriptions
millenialify tones
```

#### CLI Options

| Flag | Short | Description |
|---|---|---|
| `--tone` | `-t` | Millennial intensity 1–5 (default: 3) |
| `--provider` | `-p` | LLM provider name (default: claude) |
| `--model` | `-m` | Model ID override (uses provider default if omitted) |
| `--output` | `-o` | Write markdown output to a file |

### Web App

```bash
uvicorn millenialifier.web:app --reload
```

Then open [http://localhost:8000](http://localhost:8000). The web UI supports URL input and file uploads, provider selection, a tone slider, and real-time streamed translations via server-sent events.

## Tone Levels

| Level | Name | Vibe |
|-------|------|------|
| 1 | Light | Dinner party explanation, minimal slang |
| 2 | Moderate | Texting a smart friend, some slang |
| 3 | Balanced | PhD podcast host who brunches *(default)* |
| 4 | Heavy | Your most dramatic brilliant friend |
| 5 | UNHINGED | Chaotic group chat dissertation defense |

All levels preserve scientific accuracy — only the delivery changes.

## Project Structure

```
src/millenialifier/
├── cli.py              # Typer CLI (translate, providers, tones commands)
├── web.py              # FastAPI web app with SSE streaming
├── models.py           # Data classes: ToneLevel, Section, Paper
├── translator.py       # Core translation engine
├── prompts.py          # Tone-scaled system/user prompt templates
├── providers/
│   ├── base.py         # Abstract LLMProvider interface
│   ├── anthropic.py    # Claude provider
│   ├── openai_compat.py# OpenAI, Groq, OpenRouter, Ollama
│   └── google.py       # Gemini provider
└── parsers/
    ├── fetcher.py      # URL/file fetcher with arXiv support
    ├── pdf.py          # PDF text extraction (PyMuPDF)
    └── html.py         # HTML parsing (BeautifulSoup4)
```

## Tech Stack

- **Language:** Python 3.10+
- **CLI:** [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/)
- **Web:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) + [Jinja2](https://jinja.palletsprojects.com/)
- **PDF parsing:** [PyMuPDF](https://pymupdf.readthedocs.io/)
- **HTML parsing:** [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- **HTTP:** [httpx](https://www.python-httpx.org/) (async)
- **LLM SDKs:** Anthropic, OpenAI, Google GenAI (all optional, installed per-provider)
- **Build system:** [Hatchling](https://hatch.pypa.io/)
- **Testing:** pytest + pytest-asyncio

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE) — Dennis Myshkovskiy
