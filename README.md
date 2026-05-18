# tvtropes-mcp

[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-red?style=flat-square)](README.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python&logoColor=white)](pyproject.toml)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.2+-purple?style=flat-square)](https://github.com/jlowin/fastmcp)
[![Tests](https://img.shields.io/badge/Tests-98%20passing-brightgreen?style=flat-square)](tests/)
[![Ruff](https://img.shields.io/badge/Ruff-clean-brightgreen?style=flat-square)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Code size](https://img.shields.io/github/languages/code-size/sandraschi/tvtropes-mcp?style=flat-square)](.)

**A considerate local mirror of the TVTropes knowledge graph — polite background crawler, 12 FastMCP tools, React dashboard, LanceDB semantic search, Calibre cross-reference.**

```powershell
uv sync --extra dev
uv run python -m tvtropes_mcp --serve
# → API :10964 · dashboard :10965
```

---

## Contents

- [Architecture & Data Flow](docs/ARCHITECTURE.md) — two-process design, WAL-mode SQLite
- [Scraper Design](docs/SCRAPER.md) — politeness, Cloudflare handling, storage estimates
- [MCP Tools (12)](docs/MCP_TOOLS.md) — full reference with CLI and REST examples
- [REST API](docs/API.md) — all endpoints reference
- [Cross-MCP Bridge](docs/CROSS_MCP.md) — deep-linking from Plex, Calibre, other fleet apps
- [Ethics & Legal](docs/ETHICS_AND_LEGAL.md) — CC BY-SA 3.0, ToS, rate-limiting philosophy
- [Implementation Plan](docs/SCRAPER_PLAN.md) — full spec, crawl math, schema, risk analysis
- [Quick Start](#quick-start) — below

---

## Quick Start

```powershell
# Install
uv sync --extra dev

# Start API + MCP on :10964
uv run python -m tvtropes_mcp --serve

# Dashboard on :10965 (separate terminal)
cd web_sota && npm install && npm run dev
```

Or via the justfile:

| Command | Action |
|---------|--------|
| `just serve` | API + MCP on `:10964` |
| `just stdio` | MCP over stdio (Cursor, Claude Desktop) |
| `just scrape` | Standalone crawler daemon |
| `just test` | Run 98 tests |
| `just lint` | Ruff check |
| `just web` | Dashboard on `:10965` |

---

## Project Overview

TVTropes is an encyclopedia of narrative conventions — the closest thing we have to a formal grammar of storytelling, built collaboratively over twenty years. This project downloads that graph to your machine at a human pace and exposes it through tools that search, browse, and traverse it from your editor, local LLM, or web dashboard.

**Key properties:**
- curl_cffi with Chrome 131 TLS impersonation — passes Cloudflare free tier
- 8–15s randomised delay, 7,000 pages/day cap, exponential backoff on blocks
- Session warmup (homepage fetch) establishes cookies before crawling
- SQLite storage with WAL mode for concurrent scraper + reader access
- LanceDB vector store for semantic search via Ollama embeddings
- Ollama extraction (Qwen 2.5) converts cached HTML to structured tropes
- Calibre integration: auto-discovers metadata.db, cross-references books
- Cross-MCP bridge: other fleet apps link via `?lookup=Namespace/PageName`

---

## Dependencies

```
curl_cffi      Chrome TLS impersonation
apscheduler    Background crawl scheduler
beautifulsoup4+lxml  HTML parsing
fastmcp+fastapi+uvicorn  MCP server + REST API
httpx          Ollama async client
lancedb+pyarrow+numpy  Vector store
```

SQLite is stdlib. No external database required.

---

## License

Code: MIT. Mirror database: CC BY-SA 3.0 (derived from TVTropes content). See [LICENSE](LICENSE) and [docs/ETHICS_AND_LEGAL.md](docs/ETHICS_AND_LEGAL.md).
