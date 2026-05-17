# TVTropes Scraper — Implementation Plan

**Date:** 2026-05-04  
**Status:** Planned — implementation deferred pending robofang work  
**Estimated implementation:** 2–3 days coding, 30–50 days crawling

---

## Background & Motivation

TVTropes is a PmWiki-based wiki with ~200,000–250,000 pages across ~50 namespaces. All content is CC BY-SA 3.0. Pages are server-rendered HTML (no SPA, no JS rendering required for content). The goal is a complete local mirror queryable via MCP, useful for:

- Anime/book/film recommendations cross-referenced with trope patterns
- Calibre integration — "what tropes does this book use?"
- General creative research
- Benny is not allowed near the keyboard during this project

---

## Defense Analysis (researched 2026-05-04)

### What TVTropes actually runs

- **PmWiki** — all pages at `/pmwiki/pmwiki.php/Namespace/PageName`
- **Cloudflare free tier** (almost certainly — ad-funded wiki, no enterprise budget)
- **Rate limiting / IP bans** — primary defense, soft threshold
- **Adblock detector** — JS injection added ~Oct 2025, irrelevant for content scraping
- **No meaningful honeypots** — no evidence of generative traps or hallucinated content
- **Session required** for YMMV/, adult-flagged pages — handle separately

### What does NOT work

- `requests` / `httpx` — Python TLS fingerprint detected instantly by Cloudflare
- `puppeteer-stealth` — deprecated Feb 2025, Cloudflare detects it
- `undetected-chromedriver` / `FlareSolverr` — same family, same fate
- Rotating user-agents alone — doesn't change TLS fingerprint
- Adding delays — doesn't change bot score, only helps with rate limits

### What DOES work for TVTropes specifically

**`curl_cffi`** — Python bindings to curl with Chrome's TLS stack. JA3/JA4 fingerprint matches real Chrome. No headless browser needed since TVTropes pages are server-rendered. This is the sweet spot: browser-grade TLS without the 500MB RAM per instance overhead.

Supporting tactics:
- Single persistent session (realistic cookie/session continuity)
- Vienna-appropriate headers: `Accept-Language: de-AT,de;q=0.9,en;q=0.8,ja;q=0.7`
- Rotating `Referer` simulating page-to-page navigation
- 8–15s randomised delay (human reading cadence)
- Cloudflare 200-with-blockpage detection on response body

### Cloudflare block detection (critical)

```python
BLOCK_SIGNALS = [
    "Just a moment", "Checking your browser",
    "cf-browser-verification", "Ray ID",
    "Please enable JavaScript", "DDoS protection by Cloudflare",
    "cf_clearance",
]

def is_cloudflare_blocked(html: str) -> bool:
    return any(signal in html for signal in BLOCK_SIGNALS)
```

Cloudflare sometimes returns HTTP 200 with a block page — status code alone is not reliable.

On block detection: exponential backoff starting at 30 minutes, max 4 hours. Log and skip; retry on next crawl session.

---

## URL Structure

All TVTropes content URLs follow one pattern:
```
https://tvtropes.org/pmwiki/pmwiki.php/{Namespace}/{PageName}
```

Index pages for each namespace:
```
https://tvtropes.org/pmwiki/pmwiki.php/Main/Tropes          ← all tropes A-Z
https://tvtropes.org/pmwiki/pmwiki.php/Main/Film            ← film works
https://tvtropes.org/pmwiki/pmwiki.php/Main/Anime           ← anime works
... etc
```

Sitemap: `https://tvtropes.org/sitemap.xml` — use this to bootstrap the queue.

---

## Namespace Priority & Estimates

| Priority | Namespace | Est. Pages | Notes |
|----------|-----------|-----------|-------|
| 1 | Main/ | ~30,000 | Core tropes — crawl first |
| 2 | Laconic/ | ~25,000 | Short summaries, fast parse |
| 3 | Film/ | ~15,000 | Work pages |
| 4 | Series/ | ~12,000 | TV series |
| 5 | Anime/ | ~8,000 | Obvious personal interest |
| 6 | Literature/ | ~10,000 | Books |
| 7 | VideoGame/ | ~10,000 | |
| 8 | YMMV/ | ~20,000 | Needs session cookie |
| 9 | WesternAnimation/ | ~6,000 | |
| 10 | Everything else | ~100,000 | Long tail, crawl last |

---

## Crawl Rate & Timeline

```
Delay:          8–15 seconds randomised (uniform distribution)
Effective rate: ~5,000–7,000 pages/day
Total pages:    ~220,000 (estimated)
Wall time:      31–44 days at sustained rate
Storage:        ~15–25 GB raw HTML (gzip compressed per-page)
DB size:        ~2–4 GB structured SQLite after Ollama extraction
```

This is intentionally conservative. TVTropes serves ads; we're not trying to DoS them.

The scraper can run indefinitely in the background on Goliath without affecting normal workloads — it's I/O bound (network sleep dominates) and uses negligible CPU between requests.

---

## Database Schema

```sql
-- Queue and crawl state
CREATE TABLE pages (
    id          INTEGER PRIMARY KEY,
    url         TEXT UNIQUE NOT NULL,
    namespace   TEXT,
    page_name   TEXT,
    status      TEXT DEFAULT 'pending',  -- pending|crawled|failed|skipped
    crawled_at  TEXT,
    retry_count INTEGER DEFAULT 0,
    http_status INTEGER,
    blocked     BOOLEAN DEFAULT 0,
    content_hash TEXT
);

-- Extracted structured content
CREATE TABLE tropes (
    id          INTEGER PRIMARY KEY,
    namespace   TEXT NOT NULL,
    page_name   TEXT NOT NULL,
    title       TEXT,
    description TEXT,
    laconic     TEXT,          -- from Laconic/ namespace
    image_url   TEXT,
    extracted_at TEXT,
    UNIQUE(namespace, page_name)
);

-- Trope examples (work → trope mappings)  
CREATE TABLE examples (
    id          INTEGER PRIMARY KEY,
    trope_ns    TEXT NOT NULL,
    trope_name  TEXT NOT NULL,
    work_ns     TEXT,
    work_name   TEXT,
    example_text TEXT,
    FOREIGN KEY(trope_ns, trope_name) REFERENCES tropes(namespace, page_name)
);

-- Trope relationships (SubTrope, SuperTrope, SisterTrope, etc.)
CREATE TABLE trope_relations (
    id          INTEGER PRIMARY KEY,
    from_ns     TEXT NOT NULL,
    from_name   TEXT NOT NULL,
    relation    TEXT NOT NULL,  -- SubTrope|SuperTrope|SisterTrope|Related
    to_ns       TEXT NOT NULL,
    to_name     TEXT NOT NULL,
    UNIQUE(from_ns, from_name, relation, to_ns, to_name)
);

-- Work → trope index
CREATE TABLE work_tropes (
    id          INTEGER PRIMARY KEY,
    work_ns     TEXT NOT NULL,
    work_name   TEXT NOT NULL,
    trope_ns    TEXT NOT NULL,
    trope_name  TEXT NOT NULL,
    UNIQUE(work_ns, work_name, trope_ns, trope_name)
);

-- FTS virtual table over tropes
CREATE VIRTUAL TABLE tropes_fts USING fts5(
    page_name, title, description, laconic,
    content=tropes, content_rowid=id
);

-- Crawl session log
CREATE TABLE crawl_log (
    id          INTEGER PRIMARY KEY,
    session_id  TEXT,
    started_at  TEXT,
    ended_at    TEXT,
    pages_crawled INTEGER DEFAULT 0,
    pages_blocked INTEGER DEFAULT 0,
    errors      INTEGER DEFAULT 0
);
```

---

## Ollama Extraction Pass

The Ollama pass runs **asynchronously against cached HTML** — completely decoupled from the network crawl. Two separate queues:

1. **Crawl queue** → downloads HTML, saves to `scraper/cache/{hash}.html.gz`, marks `status=crawled` in DB
2. **Extract queue** → picks up `status=crawled` pages, calls Ollama, writes to `tropes` / `examples` / `trope_relations` tables, marks `status=extracted`

**Ollama prompt (Qwen3.5 27B Q4, ~40 tok/s on Goliath):**

```
You are extracting structured data from a TVTropes wiki page.
Extract:
1. title: the trope or work name (string)
2. description: the main description paragraph (string, max 500 chars)
3. laconic: one-sentence summary if present (string or null)  
4. examples: list of {work_namespace, work_name, example_text} (array, max 50)
5. related: list of {relation_type, namespace, page_name} for SubTrope/SuperTrope/SisterTrope links
6. categories: list of category names from the page footer

Respond ONLY with valid JSON. No markdown, no preamble.
```

Expected throughput: ~3–5 pages/minute on Qwen3.5 27B Q4 (extraction is short-context).
The extraction queue will lag the crawl queue by days initially, which is fine.

---

## Crawler State Machine

```
URL discovered
    → INSERT INTO pages (status='pending')
    
Scheduler wakes (every 8-15s)
    → SELECT url FROM pages WHERE status='pending' ORDER BY RANDOM() LIMIT 1
    → curl_cffi GET with session
    → if is_cloudflare_blocked(): mark blocked, exponential backoff
    → if http_status != 200: mark failed, increment retry_count
    → if retry_count > 5: mark skipped
    → else: save to cache, mark crawled, extract new URLs from page links, INSERT new pending URLs
    
Extractor (separate asyncio task, runs continuously)
    → SELECT url FROM pages WHERE status='crawled' LIMIT 10
    → read from cache
    → call Ollama
    → write to tropes/examples/relations tables
    → mark extracted
```

---

## Politeness Config (`scraper/config.yaml`)

```yaml
crawl:
  min_delay_s: 8
  max_delay_s: 15
  max_retries: 5
  backoff_base_minutes: 30
  backoff_max_hours: 4
  daily_budget: 7000        # hard cap — stop for the day after this many pages
  session_rotate_every: 500  # new curl_cffi session after N requests

headers:
  accept_language: "de-AT,de;q=0.9,en;q=0.8,ja;q=0.7"
  accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

namespaces:
  priority:
    - Main
    - Laconic
    - Film
    - Series
    - Anime
    - Literature
    - VideoGame
  skip:
    - SandBox
    - Administrivia
    - JustForFun    # optional, add later

ollama:
  url: "http://localhost:11434"
  model: "qwen2.5:27b"
  timeout_s: 120
  concurrent: 2   # two Ollama calls in parallel max
```

---

## Implementation Phases

### Phase 0 — Scaffold (done, 2026-05-04)
- Repo structure, plan docs, fleet index entry

### Phase 1 — Scraper Core (~1 day)
- `scraper/crawler.py` — curl_cffi session, politeness, block detection, cache
- `scraper/db.py` — SQLite schema, queue operations
- `scraper/scheduler.py` — APScheduler wrapper, daily budget enforcement
- `scraper/bootstrap.py` — sitemap fetch + namespace index crawl to seed queue
- Basic `start.ps1` — starts scheduler as background process

### Phase 2 — Ollama Extraction (~1 day)
- `scraper/extractor.py` — reads cache, calls Ollama, writes structured tables
- `scraper/parser.py` — BeautifulSoup HTML parsing helpers (URL extraction, link classification)
- FTS table population

### Phase 3 — MCP Server (~1 day)
- `src/tvtropes_mcp/server.py` — FastMCP 3.2 + Starlette
- All 8 MCP tools
- `src/tvtropes_mcp/db.py` — read-only query layer
- Basic React dashboard (scraper status + trope search UI)
- Full `start.ps1` with naked-PC compliance

### Phase 4 — Calibre Integration (later)
- `calibreops` tool extension: `trope_lookup_by_title(title)`
- Cross-reference Calibre book metadata with TVTropes Literature/ namespace
- Recommendation engine: "books with similar trope profiles"

---

## Files To Create (Phase 1+)

```
tvtropes-mcp/
├── scraper/
│   ├── crawler.py          # curl_cffi session, fetch, block detection
│   ├── db.py               # SQLite schema + queue ops
│   ├── scheduler.py        # APScheduler daemon
│   ├── bootstrap.py        # sitemap + index seed
│   ├── extractor.py        # Ollama extraction pass
│   ├── parser.py           # BeautifulSoup helpers
│   └── config.yaml         # politeness + Ollama config
├── src/tvtropes_mcp/
│   ├── __init__.py
│   ├── server.py           # FastMCP 3.2 MCP server
│   └── db.py               # read-only query layer
├── data/                   # gitignored — SQLite DB lives here
├── scraper/cache/          # gitignored — compressed HTML cache
├── docs/
│   ├── SCRAPER_PLAN.md     # this file
│   └── ARCHITECTURE.md
├── tests/
├── pyproject.toml
├── start.ps1
└── start.bat
```

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| IP ban from aggressive rate | Low at 8-15s delay | Exponential backoff; if banned, add Goliath home IP to allowlist via VPN rotation |
| Cloudflare tier upgrade by TVTropes | Low | They're ad-funded, free tier is fine for them; curl_cffi handles free tier |
| PmWiki structure change | Medium (over months) | Parser is separate from crawler; update parser.py independently |
| Ollama extraction quality | Medium | Prompt iteration; worst case raw HTML is still stored and re-processable |
| Storage overflow | Low | 25GB peak is trivial on Goliath (~30TB) |
| TVTropes going behind login | Very low | They've been public for 20 years; YMMV already handled separately |
