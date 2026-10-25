# Onboarding — tvtropes-mcp

## What this is

A local mirror of TV Tropes: a polite crawler indexes `tvtropes.org` into
SQLite (FTS5) on your machine, and 16 MCP tools + a React dashboard search
it. No account, no API key, no cloud. The wrappee is the public TV Tropes
wiki (CC BY-SA); the extractor optionally uses a local Ollama model.

## What you need

1. **This repo serving**: `just serve` (backend 10964) and the dashboard
   (`just web-dev`, port 10965 — or the Tauri app, `just build-native`).
2. **A populated DB.** A fresh checkout has an empty mirror — search
   returns nothing and that is expected, not broken.
3. **Optional: Ollama** (`http://localhost:11434`, model `qwen2.5:27b`)
   for structured extraction + semantic search. Without it the crawler
   stores pages and the HTML-fallback extractor still fills tropes.

## First run (5 minutes)

1. Open the dashboard → **Crawl a page to index it** card.
2. Pick a starter (e.g. `Anime/Planetarian`), depth 1, press **Crawl**.
3. Watch **Background Scraper** counters move; then **Search** the trope.
4. Check `scraper_status` (tool or dashboard KPI) — pending/crawled/
   extracted tells you the mirror is alive.

For bulk fill, `POST /api/scraper/start` runs the polite full crawl
(8–15 s/page, ~7 000 pages/day budget — this takes weeks, by design).

## Is it working?

- `GET /api/health` → `{"status": "ok"}`
- `GET /api/status` → `db.tropes > 0` after your first crawl
- MCP `scraper_status` → same numbers inside Claude Desktop

## Mock-until-onboarded

Until the first crawl completes, KPI cards show `—`/empty states rather
than sample numbers. There are no fake tropes: an empty DB renders empty
results with a pointer to the crawl card.
