# TVTropes Scraper Design

## Ethical Stance

The mirror exists because the knowledge is genuinely irreplaceable — there is no other source for this data at this scale and depth — and because the site's long-term availability is not guaranteed. Every technical decision is geared toward **minimizing impact**:

| Property | Value |
|----------|-------|
| **Delay between requests** | 8–15 seconds, randomised uniformly |
| **Sessions rotated** | Every 500 requests (fresh TLS context) |
| **Daily hard cap** | 7,000 pages per day (≈14 hours of crawling) |
| **Total wall time** | Estimated 30–50 days for full mirror |
| **Block behaviour** | Exponential backoff: 30 min → 2h → 4h |
| **Content scope** | Public pages only — no login bypass, no restricted content |
| **Cache lifetime** | Raw HTML stored once; re-extraction uses local cache |
| **Extraction** | Runs locally via Ollama — zero external API calls |

The scraper is designed to be **less load than a single human browsing at a normal reading pace**.

## Politeness Configuration

Defined in [`scraper/config.yaml`](../scraper/config.yaml):

```yaml
crawl:
  min_delay_s: 8
  max_delay_s: 15
  max_retries: 5
  backoff_base_minutes: 30
  backoff_max_hours: 4
  daily_budget: 7000
  session_rotate_every: 500

headers:
  accept_language: "de-AT,de;q=0.9,en;q=0.8,ja;q=0.7"

namespaces:
  priority: [Main, Laconic, Film, Series, Anime, Literature, VideoGame, ...]
  skip: [SandBox, Administrivia, Ptitle]
```

Every request passes Cloudflare block detection that inspects the **response body** (not just status code), because Cloudflare often returns HTTP 200 with a challenge page. Detected blocks trigger exponential backoff, not retry storms.

## Cloudflare Handling

TVTropes uses Cloudflare free tier. The crawler uses `curl_cffi` with Chrome 131 TLS impersonation — Python's native TLS stack (`requests`/`httpx`) is detected as a bot before any HTTP headers are exchanged. This is the same JA3/JA4 fingerprint a real Chrome user presents.

**What we do NOT do:** execute JavaScript challenges, solve CAPTCHAs, rotate residential proxies, or access authenticated content. If TVTropes deploys stronger protection, we index less content.

See [ETHICS_AND_LEGAL.md](ETHICS_AND_LEGAL.md) for the full legal and ethical discussion.

## Storage Estimates

| Resource | Size | Notes |
|----------|------|-------|
| SQLite database | 2–4 GB | Structured tropes, examples, relationships, FTS index |
| HTML cache | 15–25 GB | gzip per-page, organised by SHA-256 prefix |
| Total pages | ~200,000–250,000 | All public namespaces |
| Wall time | 30–50 days | At 5,000–7,000 pages/day |

## Crawler Implementation

See [`scraper/crawler.py`](../scraper/crawler.py) and [`docs/SCRAPER_PLAN.md`](SCRAPER_PLAN.md) for the full implementation plan including:

- curl_cffi session management with Chrome 131 impersonation
- Session warmup (homepage fetch establishes cookies + browsing context)
- gzip HTML cache organised by SHA-256 prefix
- URL extraction via BeautifulSoup, depth-limited BFS crawling
- Ollama extraction prompt for structured data (title, description, laconic, examples, relations)
- Link classification and namespace-priority queue seeding
