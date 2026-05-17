# TVTropes MCP — Architecture

## System Overview

Two independent processes sharing one SQLite database.

```
Goliath (background, always-on)          On-demand
─────────────────────────────────        ─────────────────────
scraper/scheduler.py (APScheduler)  ──▶  src/tvtropes_mcp/server.py
  │  wakes every 8-15s                     FastMCP 3.2 + Starlette
  │  curl_cffi fetch                        Port 10964 (MCP/API)
  │  save to cache/                         Port 10965 (dashboard)
  │                                         
  ▼                                        
scraper/extractor.py (asyncio)             
  │  reads cache/                           
  │  calls Ollama Qwen3.5 27B              
  │  writes structured data                 
  │                                        
  ▼                                        
data/tvtropes.db ◀───────────────────────▶ data/tvtropes.db
  pages (crawl queue/state)                 (read-only queries)
  tropes (structured content)              
  examples (work→trope mappings)           
  trope_relations (graph edges)            
  work_tropes (work→trope index)           
  tropes_fts (FTS5 virtual table)          
  crawl_log (session history)             
```

## Key Design Decisions

**curl_cffi not requests/httpx** — Chrome TLS fingerprint (JA3/JA4) essential for Cloudflare bypass. Python's TLS stack is detected before headers are read. curl_cffi is the minimum viable solution without running a full headless browser.

**SQLite not Postgres** — Single-user, single-machine, no concurrency pressure. SQLite WAL mode handles the writer (crawler/extractor) + reader (MCP server) pattern cleanly. Zero ops overhead.

**Cache-first, extract-second** — Raw HTML stored compressed before Ollama processes it. This means: (a) re-extraction is possible if the prompt changes; (b) network crawl and LLM extraction run at different speeds without blocking each other; (c) crash recovery is trivial — just re-run the extractor against cached files.

**Stateless MCP server** — The MCP server is read-only against the DB. It can be stopped and started freely without affecting the scraper. The scraper runs 24/7; the MCP server runs when Claude Desktop is open.

## Data Flow

```
1. bootstrap.py seeds pages table from sitemap.xml + namespace index pages
2. scheduler.py wakes every 8-15s, picks next pending URL
3. curl_cffi fetches URL with Chrome TLS + session cookies
4. Block detection on response body (not just status code)
5. On success: gzip HTML to cache/{sha256[:2]}/{sha256}.html.gz
6. Extract new URLs from <a href> links matching tvtropes URL pattern
7. Insert new URLs into pages table (IGNORE if already exists)
8. extractor.py (running parallel asyncio loop) picks crawled pages
9. Calls Ollama with extraction prompt → structured JSON
10. Writes to tropes, examples, trope_relations, work_tropes tables
11. Updates FTS5 index
12. MCP server queries DB on demand
```

## Ports

| Port | Service |
|------|---------|
| 10964 | MCP SSE + REST API (FastMCP 3.2 http_app) |
| 10965 | React dashboard (scraper status, trope search) |

## Storage Layout

```
data/
  tvtropes.db          # structured data + crawl state (~2-4GB final)
scraper/
  cache/
    ab/                # first 2 chars of sha256
      abcdef...html.gz # one file per crawled page (~15-25GB total)
    ...
  config.yaml
```

Both `data/` and `scraper/cache/` are gitignored. The repo is code-only.

## Process Management

Scraper runs as a background PowerShell job started by `start.ps1`. Two components:
- **Scheduler** (main loop) — APScheduler in-process, single thread, one request at a time
- **Extractor** (asyncio task) — runs in same process as async background task, max 2 concurrent Ollama calls

MCP server is a separate process started separately, or optionally co-started by `start.ps1`.

Both write to the same SQLite DB using WAL mode — safe for concurrent access.
