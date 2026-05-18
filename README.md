# tvtropes-mcp

[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-red?style=flat-square)](README.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python&logoColor=white)](pyproject.toml)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.2+-purple?style=flat-square)](https://github.com/jlowin/fastmcp)
[![Tests](https://img.shields.io/badge/Tests-63%20passing-brightgreen?style=flat-square)](tests/)
[![Ruff](https://img.shields.io/badge/Ruff-clean-brightgreen?style=flat-square)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Code size](https://img.shields.io/github/languages/code-size/sandraschi/tvtropes-mcp?style=flat-square)](.)

**A considerate, long-running local mirror of the TVTropes knowledge graph, served through FastMCP tools, a React dashboard, and Calibre cross-reference.**

```powershell
uv sync --extra dev
uv run python -m tvtropes_mcp --serve
# → API on :10964, dashboard on :10965
```

---

## What This Is

TVTropes is an encyclopedia of narrative conventions — the patterns, devices, and recurring motifs that underpin every story ever told. It's the closest thing we have to a formal grammar of storytelling, built collaboratively over twenty years by hundreds of thousands of contributors. Every trope page contains definitions, examples drawn from specific works, and links to related tropes, creating an enormous directed graph of narrative structure.

This project downloads that graph to your own machine over the course of several weeks — at a deliberately human pace — and exposes it through tools that let you search, browse, and traverse it from your code editor, your local LLM, or a web dashboard.

**The result is a private, offline, queryable copy of one of the internet's most culturally significant creative resources.**

---

## The Cultural Context

TVTropes holds an unusual position on the internet. It is simultaneously:

- **One of the largest collaboratively-built knowledge bases in existence**, comparable in scope to a mid-size Wikipedia but focused entirely on narrative craft. The article depth is often greater — many trope pages run to thousands of words with dozens of cited examples.

- **A fundamental reference for working creators.** Screenwriters check it. Game designers use it to understand genre expectations. Novelists browse it for inspiration. Showrunners are aware of it (several have referenced it in commentary tracks). The vocabulary it codified — "Chekhov's Gun," "Fridge Logic," "Jumping the Shark," "The Darkest Hour" — has seeped into everyday discourse about media.

- **An indispensable tool for anime and manga fandom.** Communities that were early adopters drove enormous growth; the Anime/ and Manga/ namespaces are among the most densely populated on the site. Trope discussions are a staple of forum culture across Crunchyroll, Reddit, 4chan's /a/, and MyAnimeList. For fans of seasonal anime in particular, the site is consulted daily.

- **A quiet backbone for AI-assisted creative work.** The structured trope-to-example mapping is uniquely suited for retrieval-augmented generation, character consistency checking, and narrative planning. The fact that this isn't more widely discussed is partly due to the site's fragility — nobody wants to be the reason TVTropes goes behind Cloudflare's Enterprise tier.

**All of this happens mostly under the radar.** TVTropes is ad-supported, runs on PmWiki, and has never had the engineering budget of a major platform. It persists through a combination of community loyalty and the fact that most of its users are read-only consumers who don't hammer the servers. That's why this project exists: to provide a safety copy that reduces the incentive to scrape aggressively, because the data is already mirrored locally.

---

## Ethical Scraping Stance

This project treats scraping as a last resort, not a default. The mirror exists because the knowledge is genuinely irreplaceable — there is no other source for this data at this scale and depth — and because the site's long-term availability is not guaranteed. Every technical decision in the scraper is geared toward **minimizing impact**:

| Property | Value |
|----------|-------|
| **Delay between requests** | 8–15 seconds, randomised uniformly |
| **Sessions rotated** | Every 500 requests (fresh TLS context) |
| **Daily hard cap** | 7,000 pages per day (≈14 hours of crawling) |
| **Total wall time** | Estimated 30–50 days for full mirror |
| **Block behaviour** | Exponential backoff: 30 min → 2h → 4h |
| **Content scope** | Public pages only — no login bypass, no restricted content |
| **Cache lifetime** | Raw HTML is stored once; re-extraction uses local cache |
| **Extraction** | Runs locally on your own machine via Ollama — zero external API calls |

The scraper is designed to be **less load than a single human browsing the site at a normal reading pace**. One person clicking through TVTropes at 2 AM on a Friday night generates more server load than this crawler does.

---

## Legal & Copyright

All TVTropes content is distributed under the **Creative Commons Attribution-ShareAlike 3.0** license (CC BY-SA 3.0). This explicitly permits copying, adaptation, and redistribution, provided that derivative works are shared under the same license. The project's own code is MIT-licensed; the mirror database is a CC BY-SA 3.0 derivative work.

**What this means in practice:**
- You may download, query, and use the mirror data for personal creative work.
- You may redistribute the structured data if you also license it CC BY-SA 3.0.
- You may **not** republish the data behind a paywall or under a more restrictive license.
- The scraper does **not** circumvent authentication, access restricted namespaces (e.g., YMMV pages that require login), or bypass intentional blocks beyond whatever Cloudflare's free tier throws at it.

See [docs/ETHICS_AND_LEGAL.md](docs/ETHICS_AND_LEGAL.md) for the full discussion, including TVTropes' specific ToS considerations and the legal rationale for local mirroring.

---

## Quick Start

### Prerequisites

- Python 3.11+ with `uv` (or pip)
- Node.js 18+ (for the dashboard)
- Optional: [Ollama](https://ollama.com) with a Qwen 2.5 model for structured extraction

### Install & Run

```powershell
# Install Python dependencies
uv sync --extra dev

# Start the API + MCP server (port 10964)
uv run python -m tvtropes_mcp --serve

# In another terminal, start the dashboard (port 10965)
cd web_sota && npm install && npm run dev
```

Or use the justfile:

| Command | Does |
|---------|------|
| `just serve` | Start API + MCP HTTP on `:10964` |
| `just stdio` | MCP over stdio (Cursor, Claude Desktop) |
| `just scrape` | Standalone background crawler daemon |
| `just test` | Run the 63-test suite |
| `just lint` | Ruff check on all Python |
| `just web` | Start the React dev dashboard on `:10965` |

---

## Architecture

```
┌────────────────────────────────┐      ┌──────────────────────────────┐
│  Background Scraper             │      │  MCP Server                   │
│  ─────────────────              │      │  ─────────────────            │
│  APScheduler wakes every 8-15s  │      │  FastMCP 3.2 + FastAPI        │
│  curl_cffi (Chrome TLS) fetch   │      │  Port 10964 (MCP + API)       │
│  Block detection (HTTP 200 body)│    ──▶  Port 10965 (React dashboard) │
│  gzip HTML → scraper/cache/     │      │  11 MCP tools                 │
│  Link extraction → queue new    │      │  Calibre cross-reference      │
│                                 │      │                              │
│  Ollama extractor (async):      │      │                              │
│  reads cached HTML, prompts     │      │                              │
│  Qwen 2.5, writes structured    │      │                              │
│  data to DB                     │      │                              │
└────────────────────────────────┘      └──────────────────────────────┘
              │                                      │
              ▼                                      ▼
       data/tvtropes.db                       data/tvtropes.db
       scraper/cache/                   (shared WAL-mode SQLite)
```

The scraper and MCP server are **decoupled processes** that share a single SQLite database in WAL mode. The scraper runs for weeks in the background (it's I/O-bound — network sleep dominates). The MCP server is read-only and can be stopped and started freely. The Ollama extraction pass runs asynchronously against the local cache, completely independent of the network crawl.

---

## MCP Tools (11)

All tools are registered via `@mcp.tool` decorators in [`src/tvtropes_mcp/server.py`](src/tvtropes_mcp/server.py) and query the local SQLite mirror. Every tool is annotated `readOnlyHint` — the mirror is never modified by queries.

| Tool | Args | Description |
|------|------|-------------|
| `trope_search` | `query`, `limit` | Full-text FTS5 search across all trope names and descriptions |
| `trope_get` | `trope_id` | Full trope page: description, laconic summary, examples, all relationship types |
| `work_tropes` | `work_id` | All tropes associated with a work (e.g., `Series/BreakingBad`) |
| `trope_examples` | `trope_id`, `namespace?`, `limit` | Examples filtered by medium (Film, Anime, Literature...) |
| `related_tropes` | `trope_id` | Graph traversal: SubTrope, SuperTrope, SisterTrope, Related |
| `namespace_list` | — | All namespaces with page counts |
| `random_trope` | — | Random trope weighted by example count |
| `scraper_status` | — | Crawl progress, DB size, Ollama backlog |
| `trope_lookup_by_title` | `title` | Cross-reference a book title against the Literature/ namespace |
| `calibre_search` | `title?`, `author?`, `limit` | Search your local Calibre library |
| `calibre_status` | — | Check if a Calibre library is detected |

### Example Usage (via MCP CLI)

```powershell
uv run python -m tvtropes_mcp --stdio
# Then in any MCP client:
# trope_search("villain redemption", limit=5)
# trope_get("Main/ChekhovsGun")
# work_tropes("Series/NeonGenesisEvangelion")
# related_tropes("Main/FiveManBand")
```

### Example Usage (via REST API)

```powershell
# Call any MCP tool through the REST proxy
curl -X POST http://127.0.0.1:10964/api/mcp/tool \
  -H "Content-Type: application/json" \
  -d '{"name": "trope_search", "args": {"query": "time loop", "limit": 3}}'

curl -X POST http://127.0.0.1:10964/api/mcp/tool \
  -H "Content-Type: application/json" \
  -d '{"name": "trope_get", "args": {"trope_id": "Main/ChekhovsGun"}}'
```

---

## CLI Flags

| Flag | Transport | Use case |
|------|-----------|----------|
| `--serve` | Streamable HTTP (SSE) | FastAPI + MCP on port 10964 |
| `--stdio` | stdio | Claude Desktop, Cursor, any StdioClientTransport |
| `--scrape` | — | Standalone scraper daemon (no MCP server) |
| `--debug` | — | Verbose logging to stderr |

---

## REST API

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
| GET | `/api/calibre/status` | Calibre library availability |
| GET | `/api/calibre/search` | Search Calibre books by title/author |

---

## Scraper Politeness Details

The scraper enforces a strict politeness regime documented in [`scraper/config.yaml`](scraper/config.yaml):

```
crawl:
  min_delay_s: 8           # never faster than 8 seconds
  max_delay_s: 15          # never faster than 15 seconds
  max_retries: 5           # give up after 5 failures
  backoff_base_minutes: 30 # first backoff: 30 minutes
  backoff_max_hours: 4     # cap backoff at 4 hours
  daily_budget: 7000       # hard stop for the day
  session_rotate_every: 500

headers:
  accept_language: "de-AT,de;q=0.9,en;q=0.8,ja;q=0.7"

namespaces:
  priority: [Main, Laconic, Film, Series, Anime, ...]
  skip: [SandBox, Administrivia, Ptitle]
```

Every request passes through Cloudflare block detection that inspects the **response body** (not just the status code), because Cloudflare often returns HTTP 200 with a challenge page. Detected blocks trigger exponential backoff, not retry storms.

---

## Storage Estimates

| Resource | Size | Notes |
|----------|------|-------|
| SQLite database | 2–4 GB | Structured data: tropes, examples, relationships, FTS index |
| HTML cache | 15–25 GB | gzip-compressed per-page HTML, organised by SHA-256 prefix |
| Total pages | ~200,000–250,000 | Across all public namespaces |
| Wall time | 30–50 days | At 5,000–7,000 pages/day |

---

## Anti-Scraping Measures We Document Transparently

TVTropes uses Cloudflare's free tier. This project employs **no** measures to bypass intentional blocks — it uses `curl_cffi` to present a Chrome-compatible TLS fingerprint because Python's native TLS stack (`requests`/`httpx`) is detected as a bot before any HTTP headers are exchanged. This is the same technique a real Chrome user employs automatically.

We document this honestly because transparency about scraping methodology is the only thing that separates responsible mirroring from hostile extraction. If TVTropes deploys stronger detection (e.g., challenges that require JavaScript execution, or Cloudflare Enterprise-grade protections), this project will respect them — it will simply index less content.

---

## Dependencies

```
curl_cffi>=0.7        Chrome TLS impersonation
apscheduler>=3.10     Background crawl scheduler
beautifulsoup4>=4.12  HTML parsing
lxml>=5.0             Fast BS4 parser
fastmcp>=3.2.4        MCP server framework
fastapi>=0.115.0      REST API
uvicorn[standard]     ASGI server
httpx>=0.27           Ollama async client
pyyaml>=6.0           Configuration
pydantic-settings>=2  Environment-based config
```

SQLite is stdlib. No external database required.

---

## License

The project code is MIT. The mirror database it produces (all downloaded TVTropes content) is a derivative work under CC BY-SA 3.0, inheriting the original license. See [LICENSE](LICENSE) and [docs/ETHICS_AND_LEGAL.md](docs/ETHICS_AND_LEGAL.md).
