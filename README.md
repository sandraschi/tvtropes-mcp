# tvtropes-mcp

[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-red?style=flat-square)](README.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python&logoColor=white)](pyproject.toml)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.2+-purple?style=flat-square)](https://github.com/jlowin/fastmcp)
[![Tests](https://img.shields.io/badge/Tests-63%20passing-brightgreen?style=flat-square)](tests/)
[![Ruff](https://img.shields.io/badge/Ruff-clean-brightgreen?style=flat-square)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Code size](https://img.shields.io/github/languages/code-size/sandraschi/tvtropes-mcp?style=flat-square)](.)

**TVTropes local mirror + MCP server** — polite background crawler that builds a SQLite mirror of tvtropes.org, serves it via 11 FastMCP tools, with a React dashboard and Calibre cross-reference.

---

## Quick Start

```powershell
uv sync --extra dev                         # install deps
uv run python -m tvtropes_mcp --serve        # start API + MCP on :10964
# Open http://127.0.0.1:10965                # React dashboard
```

Or via the justfile:
```powershell
just serve        # API + MCP HTTP
just stdio        # MCP over stdio (Cursor/Claude Desktop)
just scrape       # standalone scraper daemon
just test         # 63 tests
```

---

## Two-Part Architecture

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  Background Scraper          │     │  MCP Server                   │
│  crawler.py (curl_cffi)      │────▶│  FastMCP 3.2 + FastAPI        │
│  APScheduler daemon          │     │  Ports 10964/10965            │
│  Ollama extraction pass      │     │  11 MCP tools                 │
│  SQLite state + HTML cache   │     │  React dashboard              │
└─────────────────────────────┘     └──────────────────────────────┘
             │                              │
             ▼                              ▼
      data/tvtropes.db              data/tvtropes.db
      scraper/cache/               (shared read/write WAL)
```

The scraper and MCP server are **decoupled** — they share only the SQLite DB (WAL mode).

---

## MCP Tools (11)

| Tool | Description |
|------|-------------|
| `trope_search` | Full-text FTS5 search over trope names and descriptions |
| `trope_get` | Full trope page — description, examples, sub/super/sister tropes |
| `work_tropes` | All tropes for a given work (e.g. `Series/BreakingBad`) |
| `trope_examples` | Examples filtered by namespace/medium |
| `related_tropes` | Graph traversal — SubTrope, SuperTrope, SisterTrope, Related |
| `namespace_list` | List all namespaces and page counts |
| `random_trope` | Random trope (weighted by example count) |
| `scraper_status` | Crawl progress, DB size, extraction backlog |
| `trope_lookup_by_title` | Cross-reference book title against Literature/ namespace |
| `calibre_search` | Search local Calibre library by title or author |
| `calibre_status` | Check Calibre library availability |

---

## Scraper Design

See [docs/SCRAPER_PLAN.md](docs/SCRAPER_PLAN.md) for full detail.

- `curl_cffi` with Chrome TLS impersonation — looks like a real browser
- 8–15s randomised delay between requests (human reading pace)
- ~5,000–8,000 pages/day sustainable rate
- Cloudflare block detection on HTTP 200 body
- Ollama extraction runs async against cached HTML (network ↔ LLM decoupled)
- Estimated total: ~200,000–250,000 pages, 30–50 days at polite rate

---

## CLI

| Flag | Transport | Use case |
|------|-----------|----------|
| `--serve` | Streamable HTTP (SSE) | FastAPI + MCP on `:10964` |
| `--stdio` | stdio | Claude Desktop, Cursor |
| `--scrape` | Standalone daemon | Background crawl |
| `--debug` | — | Verbose stderr logs |

---

## REST API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | Crawl stats, DB stats, scraper state |
| `/api/tools` | GET | List MCP tools |
| `POST /api/mcp/tool` | POST | Proxy: call any MCP tool by name+args |
| `GET /api/mcp/tools` | GET | List tool JSON schemas |
| `/api/scraper/start\|stop` | POST | Manage crawler |
| `/api/scraper/extract` | POST | Run one Ollama extraction pass |
| `/api/scraper/bootstrap` | POST | Seed URL queue from sitemap |
| `/api/calibre/status\|search` | GET | Calibre library |

---

## Ports

| Service | Port |
|---------|------|
| MCP + API backend | 10964 |
| React dashboard | 10965 |

---

## Dependencies

```
curl_cffi>=0.7        # Chrome TLS impersonation
apscheduler>=3.10     # Background scheduler
beautifulsoup4>=4.12  # HTML parsing
fastmcp>=3.2.4        # MCP server
fastapi>=0.115.0      # REST API
uvicorn[standard]     # ASGI server
httpx>=0.27           # Ollama client
```

SQLite is stdlib. No external DB required.

---

## License

MIT — see [LICENSE](LICENSE).
