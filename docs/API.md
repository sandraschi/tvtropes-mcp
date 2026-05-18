# REST API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Service health |
| GET | `/api/status` | Crawl stats, DB stats, scraper state |
| GET | `/api/tools` | List registered MCP tools |
| POST | `/api/mcp/tool` | Proxy: call any MCP tool by name + args |
| GET | `/api/mcp/tools` | List tool JSON schemas |
| POST | `/api/scraper/start` | Start the background crawler |
| POST | `/api/scraper/stop` | Stop the background crawler |
| GET | `/api/scraper/status` | Scraper process health |
| POST | `/api/scraper/extract` | Run one Ollama extraction pass |
| POST | `/api/scraper/bootstrap` | Seed URL queue from sitemap.xml |
| POST | `/api/scraper/crawl` | Crawl from a starting URL with depth limit |
| GET | `/api/pages` | List crawled pages (filterable by status/namespace) |
| GET | `/api/pages/{id}/content` | View cached body content of a crawled page |
| GET | `/api/calibre/status` | Calibre library availability |
| GET | `/api/calibre/search` | Search Calibre books by title/author |
| GET | `/api/bridge` | Fleet bridge metadata for cross-MCP linking |
| GET | `/api/lookup/title` | Resolve title to page path |
| GET | `/api/settings` | User settings from `data/settings.json` |
| POST | `/api/settings` | Update and persist settings |
| GET | `/api/ollama/status` | Check Ollama/LMStudio connectivity |
| POST | `/api/ollama/test` | Test a specific host+model combination |
| GET | `/api/log` | Recent log entries |
| GET | `/api/vector/count` | LanceDB vector count |
| POST | `/api/vector/rebuild` | Rebuild vector index from all tropes |
