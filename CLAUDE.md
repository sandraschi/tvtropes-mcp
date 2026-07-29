# tvtropes-mcp — Agent Instructions

## Entry Points

```powershell
uv run python -m tvtropes_mcp --serve     # HTTP daemon (:10964)
uv run python -m tvtropes_mcp --stdio     # stdio (Claude Desktop etc.)
uv run python -m tvtropes_mcp --scrape    # Standalone scraper
```

## Key Files

| File | Purpose |
|------|---------|
| `src/tvtropes_mcp/server.py` | 13 MCP tools + 5 prompts |
| `src/tvtropes_mcp/app.py` | FastAPI REST + MCP HTTP |
| `scraper/bootstrap.py` | Seed URL discovery (sitemap, pagelist API, namespace indexes) |
| `scraper/scheduler.py` | Background crawl loop with politeness + daily budget |
| `scraper/crawler.py` | curl_cffi Chrome 131 TLS impersonation |
| `web_sota/src/` | React/Vite frontend |
| `run_server.py` | PyInstaller entry point |

## Ports

- Backend: 10964 (HTTP + MCP)
- Frontend: 10965 (Vite dev)

## Standards

- FastMCP >=3.4.4, <4
- Ruff linting
- Pre-commit hooks installed
