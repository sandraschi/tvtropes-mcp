# tvtropes-mcp

**TVTropes Local Mirror + MCP Server** — Background scraper that politely crawls tvtropes.org over weeks/months, stores everything locally, then serves it via FastMCP for use in recommendations, Calibre integration, and general trope-aware queries.

> "An old dream." — Sandra, 2026-05-04

[![Status: Scaffold](https://img.shields.io/badge/Status-Scaffold-lightgrey.svg)](README.md)

---

## Two-Part Architecture

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  Background Scraper          │     │  MCP Server                   │
│  scraper/crawler.py          │────▶│  src/tvtropes_mcp/server.py  │
│  APScheduler daemon          │     │  FastMCP 3.2 + Starlette      │
│  curl_cffi + politeness      │     │  Ports 10964/10965            │
│  SQLite state + HTML cache   │     │  Queries SQLite DB            │
│  Ollama extraction pass      │     │                               │
└─────────────────────────────┘     └──────────────────────────────┘
                    │                              │
                    ▼                              ▼
             data/tvtropes.db              data/tvtropes.db
             scraper/cache/               (shared read/write)
```

The scraper and MCP server are **decoupled** — they share only the SQLite DB. The scraper runs as a background Windows service / scheduled task. The MCP server is read-only against the DB.

---

## Scraper Design

See [docs/SCRAPER_PLAN.md](docs/SCRAPER_PLAN.md) for full detail.

**Key properties:**
- `curl_cffi` with Chrome TLS impersonation — looks like a real browser at the TLS layer
- 8–15 second randomised delay between requests (human reading pace)
- ~5,000–8,000 pages/day sustainable rate
- Full resume: SQLite queue survives restarts
- Cloudflare block detection on HTTP 200 body (not just status code)
- Ollama extraction runs async against cached HTML — network and LLM fully decoupled
- Estimated total corpus: ~200,000–250,000 pages across all namespaces
- Estimated wall time: 30–50 days at polite rate

---

## MCP Tools (planned)

| Tool | Description |
|------|-------------|
| `trope_search` | Full-text search over trope names and descriptions |
| `trope_get` | Full trope page — description, examples, related tropes |
| `work_tropes` | All tropes for a given work (film, series, anime, etc.) |
| `trope_examples` | Examples of a trope filtered by namespace/medium |
| `related_tropes` | Graph traversal — SubTrope / SuperTrope / SisterTrope |
| `namespace_list` | List all namespaces and page counts |
| `random_trope` | Random trope (weighted by example count) |
| `scraper_status` | Crawl progress, queue depth, Ollama backlog, DB stats |

---

## Ports

| Service | Port |
|---------|------|
| MCP + API backend | 10964 |
| React dashboard | 10965 |

---

## Status

**Scaffold only.** See [docs/SCRAPER_PLAN.md](docs/SCRAPER_PLAN.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Implementation deferred — robofang work takes priority.

---

## Dependencies (planned)

```
curl_cffi>=0.7        # Chrome TLS impersonation
apscheduler>=3.10     # Background scheduler
beautifulsoup4>=4.12  # HTML parsing
fastmcp>=3.2.4        # MCP server
starlette>=1.0        # Web framework
uvicorn[standard]     # ASGI server
httpx>=0.27           # Ollama client
pyyaml>=6.0           # Config
```

SQLite is stdlib. No external DB required.
