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
| `src/tvtropes_mcp/server.py` | FastMCP tool registrations (8 tools) |
| `src/tvtropes_mcp/app.py` | FastAPI REST + MCP HTTP mount at `/mcp` |
| `src/tvtropes_mcp/config.py` | All settings via env (prefix `TVTROPES_MCP_`) |
| `scraper/config.yaml` | Scraper politeness config, namespaces, Ollama settings |
| `scraper/` | Background scraper package (crawler + Ollama extraction) |
| `docs/SCRAPER_PLAN.md` | Full implementation plan — schema, crawl math, risk table |
| `docs/ARCHITECTURE.md` | System architecture and design decisions |
| `web_sota/` | React/Vite dashboard; start with `start.bat` or `npm run dev` |

## Tool Modules

| Tool | Description |
|------|-------------|
| `trope_search` | Full-text search over trope names and descriptions |
| `trope_get` | Full trope page — description, examples, related tropes |
| `work_tropes` | All tropes for a given work |
| `trope_examples` | Examples of a trope filtered by namespace/medium |
| `related_tropes` | Graph traversal — SubTrope / SuperTrope / SisterTrope |
| `namespace_list` | List all namespaces and page counts |
| `random_trope` | Random trope (weighted by example count) |
| `scraper_status` | Crawl progress, queue depth, Ollama backlog, DB stats |

## Status

**Scaffold phase.** All 8 MCP tools are registered as stubs returning deferred messages.
Scraper and database layer are planned in `docs/SCRAPER_PLAN.md` but not yet implemented.
Implementation deferred pending robofang work.

## Testing

```powershell
uv run pytest            # full suite
uv run pytest tests/ -v  # verbose
```

## Linting

```powershell
# Python
ruff check src/ tests/
ruff format src/ tests/

# Frontend (from web_sota/)
biome lint src/
biome check --write src/
```
