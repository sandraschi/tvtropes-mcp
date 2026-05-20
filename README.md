# tvtropes-mcp

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>

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
- [Installation Guide](INSTALL.md) — prerequisites, clone, config, start
- [Quick Start](#quick-start) — below

---

## Quick Start

```powershell
git clone https://github.com/sandraschi/tvtropes-mcp
cd tvtropes-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:
git clone https://github.com/sandraschi/tvtropes-mcp.git
cd tvtropes-mcp
just install     # Python deps + frontend
just serve       # API + MCP on :10964
# Dashboard: http://127.0.0.1:10965
See [INSTALL.md](INSTALL.md) for prerequisites, configuration, and MCP client setup.
Or via individual commands:

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
