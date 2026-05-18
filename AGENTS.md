# AGENTS.md — tvtropes-mcp

## Project Identity
- **Name**: tvtropes-mcp
- **Purpose**: TVTropes local mirror + MCP server — background scraper + query interface
- **Stack**: FastMCP 3.2+, FastAPI, Starlette, SQLite FTS5, curl-cffi, BeautifulSoup4
- **Ports**: 10964 (backend + MCP HTTP), 10965 (Vite dashboard)
- **Transports**: stdio (`--stdio`) and streamable HTTP (`--serve`)

## Key Files

| File | Purpose |
|------|---------|
| `src/tvtropes_mcp/server.py` | FastMCP tool registrations (11 tools) |
| `src/tvtropes_mcp/app.py` | FastAPI REST + MCP HTTP mount at `/mcp` + REST proxy at `/api/mcp/tool` |
| `src/tvtropes_mcp/config.py` | All settings via env (prefix `TVTROPES_MCP_`) |
| `src/tvtropes_mcp/db.py` | Read-only query layer for MCP tools |
| `src/tvtropes_mcp/scraper_manager.py` | Start/stop/monitor scraper from MCP process |
| `src/tvtropes_mcp/calibre_ops.py` | Calibre library discovery + book search + trope cross-ref |
| `scraper/db.py` | SQLite schema (7 tables), queue ops, FTS5 search, crawl log |
| `scraper/crawler.py` | curl_cffi session with Chrome TLS, politeness delays, gzip cache |
| `scraper/parser.py` | BeautifulSoup HTML parsing, Cloudflare detection, sitemap parsing |
| `scraper/bootstrap.py` | Seed queue from sitemap.xml + namespace index pages |
| `scraper/scheduler.py` | APScheduler crawl loop with daily budget |
| `scraper/extractor.py` | Async Ollama extraction via httpx |
| `scraper/config.yaml` | Scraper politeness config, namespaces, Ollama settings |
| `docs/SCRAPER_PLAN.md` | Full implementation plan — schema, crawl math, risk table |
| `docs/ARCHITECTURE.md` | System architecture and design decisions |
| `web_sota/` | React/Vite dashboard with TropeSearch, WorkBrowser, TropeGraph pages |

## MCP Tools (11 total)

| Tool | Description |
|------|-------------|
| `trope_search` | Full-text FTS5 search over trope names and descriptions |
| `trope_get` | Full trope page — description, examples, sub/super/sister tropes |
| `work_tropes` | All tropes for a given work (e.g. Series/BreakingBad) |
| `trope_examples` | Examples filtered by namespace/medium |
| `related_tropes` | Graph traversal — SubTrope / SuperTrope / SisterTrope / Related |
| `namespace_list` | List all namespaces and page counts |
| `random_trope` | Random trope (weighted by example count) |
| `scraper_status` | Crawl progress, DB size, extraction backlog |
| `trope_lookup_by_title` | Cross-reference book title against Literature/ namespace |
| `calibre_search` | Search local Calibre library by title or author |
| `calibre_status` | Check Calibre library availability |

## CLI

```powershell
uv run python -m tvtropes_mcp --serve     # FastAPI (HTTP + MCP streamable)
uv run python -m tvtropes_mcp --stdio     # stdio (Claude Desktop, Cursor)
uv run python -m tvtropes_mcp --scrape    # Standalone scraper daemon
uv run python -m tvtropes_mcp --help      # All flags
```

## REST API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | Crawl stats, DB stats, scraper state |
| `/api/tools` | GET | List registered MCP tools |
| `/api/mcp/tool` | POST | Proxy: call any MCP tool by name+args |
| `/api/mcp/tools` | GET | List tool schemas |
| `/api/scraper/start` | POST | Start crawler |
| `/api/scraper/stop` | POST | Stop crawler |
| `/api/scraper/status` | GET | Scraper process status |
| `/api/scraper/extract` | POST | Run one Ollama extraction pass |
| `/api/scraper/bootstrap` | POST | Seed URL queue from sitemap |
| `/api/calibre/status` | GET | Calibre library availability |
| `/api/calibre/search` | GET | Search Calibre books |

## Testing

```powershell
uv run pytest                 # 63 tests — all pass
uv run pytest -v              # verbose
just test                     # via justfile
```

## Linting

```powershell
ruff check src/ scraper/ tests/
ruff format src/ scraper/ tests/
```

## CI

Pre-commit hooks: ruff (lint+format), mypy, trailing-whitespace, yaml check.
Justfile: `test`, `lint`, `format`, `serve`, `stdio`, `scrape`, `web`.
