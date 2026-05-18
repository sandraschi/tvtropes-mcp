# tvtropes-mcp — Architecture

## Overview

Two independent processes share a single SQLite database in WAL mode. The scraper is a long-running background daemon; the MCP server is a query interface that can be started and stopped freely.

```
┌────────────────────────────────┐      ┌──────────────────────────────┐
│  Background Scraper             │      │  MCP Server                   │
│  ─────────────────              │      │  ─────────────────            │
│  APScheduler loop               │      │  FastMCP 3.2 + FastAPI        │
│  curl_cffi (Chrome TLS) fetch   │      │  Port 10964 (MCP + REST API) │
│  Block detection on body text   │    ──▶  Port 10965 (React dashboard) │
│  gzip HTML → scraper/cache/     │      │  11 MCP tools (read-only)     │
│  URL extraction → queue         │      │  REST proxy at /api/mcp/tool  │
│  Daily budget enforcement       │      │  Calibre cross-reference      │
│                                 │      │                              │
│  Ollama extractor (async):      │      │                              │
│  reads cached HTML, prompts     │      │                              │
│  local Qwen 2.5 model, writes   │      │                              │
│  structured data to DB          │      │                              │
└────────────────────────────────┘      └──────────────────────────────┘
              │                                      │
              ▼                                      ▼
       data/tvtropes.db                       data/tvtropes.db
       scraper/cache/                   (shared WAL-mode SQLite)
```

## Design Decisions

### curl_cffi not requests/httpx

Python's native TLS stack (`requests`/`httpx` using OpenSSL or MbedTLS) is reliably fingerprinted by Cloudflare as bot traffic before any HTTP headers are exchanged. `curl_cffi` exposes Chrome's TLS implementation directly, producing JA3/JA4 fingerprints indistinguishable from a real Chrome instance. This is the minimum viable approach — no headless browser, no JavaScript execution.

### SQLite not Postgres

Single-user, single-machine, no concurrency pressure. SQLite WAL mode handles the writer (scraper/extractor) + reader (MCP server) pattern cleanly. Zero operations overhead, no daemon process, no configuration. The final database is ~2–4 GB, well within SQLite's tested range.

### Cache-first, extract-second

Raw HTML is gzip-compressed to `scraper/cache/` before any structured extraction happens. This provides:

- **Re-extractability**: if the Ollama prompt improves, re-run against cached files — no network fetch needed.
- **Decoupled pipelines**: the network crawl (I/O-bound, sleeps most of the time) and the LLM extraction (CPU/GPU-bound) run at different speeds without blocking each other.
- **Crash recovery**: if the process dies mid-extraction, the worst case is re-processing a few cached files.

### Decoupled processes

The scraper and MCP server do not communicate directly. They share only the SQLite database. The scraper runs as a background daemon on a schedule. The MCP server is read-only and can be stopped, restarted, or run on different machines (if the DB is on a network drive). This means:

- The MCP server starts instantly — no crawl state to recover.
- The scraper can run 24/7 without affecting query latency.
- Either can be updated independently.

## Data Flow

```
1. bootstrap.py fetches sitemap.xml + namespace index pages
   → seeds the pages table with discoverable URLs
   
2. scheduler.py (APScheduler, wakes every 8-15s):
   → pops one pending URL from the queue
   → delegates to crawler.fetch(url)
   
3. crawler.fetch(url):
   → curl_cffi GET with Chrome TLS impersonation
   → checks response body for Cloudflare block signals
   → if blocked: exponential backoff (30min→2h→4h)
   → if success: gzip-compress HTML → cache/{hash[:2]}/{hash}.html.gz
   → returns HTML + content hash
   
4. scheduler.py marks page as crawled in pages table
   → extracts new URLs via BeautifulSoup
   → queues unseen URLs (INSERT OR IGNORE)
   
5. extractor.py (async, runs independently):
   → polls for pages with status='crawled'
   → reads cached HTML from disk
   → calls Ollama with extraction prompt
   → parses JSON response
   → writes to tropes, examples, trope_relations, work_tropes
   → syncs FTS5 index
   → marks page as extracted
   
6. MCP tools query the database:
   → trope_search → FTS5 MATCH on tropes_fts
   → trope_get → tropes + examples + trope_relations JOINs
   → work_tropes → work_tropes + tropes JOIN
   → scraper_status → pages + tropes aggregates
```

## Storage Layout

```
data/
  tvtropes.db          # SQLite database (~2-4 GB final)

scraper/
  cache/
    ab/                # first 2 hex chars of SHA-256
      abcdef...html.gz # one gzip-compressed HTML file per page
      123456...html.gz
      ...
    cd/
    ef/
    ...
  config.yaml          # crawl politeness, namespaces, Ollama settings
```

Both `data/` and `scraper/cache/` are gitignored. The repository contains code only.

## Database Schema

Seven tables plus indexes. See [scraper/db.py](../scraper/db.py) for the exact DDL.

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `pages` | Crawl queue and state | url, namespace, status, retry_count, content_hash |
| `tropes` | Structured trope data | namespace, page_name, title, description, laconic |
| `examples` | Trope→work examples | trope_ns, trope_name, work_ns, work_name, example_text |
| `trope_relations` | Trope relationship graph | from_ns, from_name, relation, to_ns, to_name |
| `work_tropes` | Work→trope index | work_ns, work_name, trope_ns, trope_name |
| `tropes_fts` | FTS5 full-text search | Virtual table over tropes (porter+unicode61 tokenizer) |
| `crawl_log` | Session history | session_id, started_at, pages_crawled, errors |

## Ports

| Port | Service | Protocol |
|------|---------|----------|
| 10964 | MCP server + FastAPI | SSE (MCP) + JSON (REST API) |
| 10965 | React dashboard | HTTP (Vite dev server) |

Both ports are registered in the fleet port registry at `mcp-central-docs`. They are in the reserved 10700–11000 range and kept adjacent per fleet convention.

## Process Management

- **Standalone mode** (`--scrape`): runs the APScheduler crawler loop indefinitely. Best for a dedicated machine (Goliath). Prints minute-by-minute stats.
- **Server mode** (`--serve`): starts the FastAPI + MCP server. The scraper can be started/stopped via REST API endpoints (`POST /api/scraper/start`, `/stop`).
- **Stdio mode** (`--stdio`): runs the MCP server over stdin/stdout for Claude Desktop, Cursor, and other StdioClientTransport consumers. No HTTP server.

## Ollama Extraction

The extraction pass runs asynchronously against cached HTML files, completely decoupled from the network crawl. It uses `httpx` to call a local Ollama instance (default: `http://localhost:11434`, model: `qwen2.5:27b`). The extraction prompt is documented in [`scraper/extractor.py`](../scraper/extractor.py) and instructs the model to produce structured JSON:

```json
{
  "title": "string or null",
  "description": "string (max 500 chars) or null",
  "laconic": "string or null",
  "examples": [{"work_namespace": "string", "work_name": "string", "example_text": "string"}],
  "related": [{"relation_type": "SubTrope|SuperTrope|SisterTrope", "namespace": "string", "page_name": "string"}]
}
```

The model is called with `temperature: 0.1` and `format: "json"` for deterministic extraction. Maximum 2 concurrent calls. If Ollama is unavailable, the extraction pass is skipped (the crawl continues unaffected).
