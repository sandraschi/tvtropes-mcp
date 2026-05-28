# AGENTS.md — tvtropes-mcp

## Project Identity
- **Name**: tvtropes-mcp
- **Purpose**: TVTropes local mirror + MCP server — polite crawler, SQLite storage, 12 MCP tools
- **Stack**: FastMCP 3.2+, FastAPI, Starlette, SQLite FTS5, curl-cffi, BeautifulSoup4, LanceDB
- **Ports**: 10964 (backend + MCP HTTP), 10965 (Vite dashboard)
- **Transports**: stdio (`--stdio`) and streamable HTTP (`--serve`)

## Key Files

| File | Purpose |
|------|---------|
| `src/tvtropes_mcp/server.py` | FastMCP tool registrations (12 tools) |
| `src/tvtropes_mcp/app.py` | FastAPI REST + MCP HTTP mount at `/mcp` |
| `src/tvtropes_mcp/config.py` | Env-based settings (prefix `TVTROPES_MCP_`) |
| `src/tvtropes_mcp/settings_manager.py` | User settings persisted to `data/settings.json` |
| `src/tvtropes_mcp/vector_store.py` | LanceDB vector store for semantic search |
| `src/tvtropes_mcp/calibre_ops.py` | Calibre library discovery + book trope cross-ref |
| `src/tvtropes_mcp/content_extractor.py` | Strip nav/footer from cached HTML for page view |
| `src/tvtropes_mcp/scraper_manager.py` | Start/stop/monitor scraper from MCP process |
| `scraper/crawler.py` | curl_cffi session, politeness, block detection, cache |
| `scraper/db.py` | SQLite schema (7 tables), queue ops, FTS5, crawl log |
| `scraper/parser.py` | BeautifulSoup parsing, Cloudflare detection, link extraction |
| `scraper/scheduler.py` | APScheduler crawl loop with daily budget |
| `scraper/extractor.py` | Async Ollama extraction from cached HTML |
| `scraper/config.yaml` | Scraper politeness config, namespaces, Ollama |
| `docs/ARCHITECTURE.md` | System architecture and design decisions |
| `docs/SCRAPER.md` | Scraper design, politeness, storage estimates |
| `docs/MCP_TOOLS.md` | All 12 MCP tools with examples |
| `docs/API.md` | REST API endpoint reference |
| `docs/CROSS_MCP.md` | Deep-link bridge for Plex/Calibre |
| `docs/ETHICS_AND_LEGAL.md` | CC BY-SA 3.0, ToS, rate-limiting philosophy |
| `docs/SCRAPER_PLAN.md` | Implementation plan, schema, crawl math |
| `web_sota/` | React/Vite dashboard (10 pages) |

## MCP Tools (12)

| Tool | Description |
|------|-------------|
| `trope_search` | Full-text FTS5 search over trope names and descriptions |
| `trope_get` | Full trope page — description, examples, sub/super/sister/related |
| `work_tropes` | All tropes for a given work |
| `trope_examples` | Examples filtered by namespace/medium |
| `related_tropes` | Graph traversal — SubTrope, SuperTrope, SisterTrope, Related |
| `namespace_list` | List all namespaces and page counts |
| `random_trope` | Random trope (weighted by example count) |
| `scraper_status` | Crawl progress, DB size, extraction backlog |
| `semantic_search` | Vector similarity search via LanceDB + Ollama embeddings |
| `trope_lookup_by_title` | Cross-reference book title against Literature/ namespace |
| `calibre_search` | Search local Calibre library by title or author |
| `calibre_status` | Check if a Calibre library is detected |

## CLI

```powershell
uv run python -m tvtropes_mcp --serve     # FastAPI (HTTP + MCP streamable)
uv run python -m tvtropes_mcp --stdio     # stdio (Claude Desktop, Cursor)
uv run python -m tvtropes_mcp --scrape    # Standalone scraper daemon
```

## Testing

```powershell
uv run pytest            # 98 tests
just test                # via justfile
```

## Linting

```powershell
ruff check src/ scraper/ tests/
ruff format src/ scraper/ tests/
```

Install docs: follow mcp-central-docs/standards/AGENT_INSTALL_REFERENCE.md
