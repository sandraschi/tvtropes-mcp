
## [Unreleased] — 2026-06-14

### Added
- Tauri native wrapper (native/ directory) with bundle.resources + std::process::Command
- CUA-NSIS: just cua-nsis-test recipe, scripts/cua-smoke.py, scripts/cua-nsis-config.json
- Tauri CORS: tauri://localhost origins for WebView API access
- NSIS installer at dist/ and native/target/release/bundle/nsis/

### Changed
- Frontend API calls use absolute http://127.0.0.1:{port} URLs in production build
- CORS middleware includes allow_origin_regex for tauri.localhost
# Changelog

All notable changes to tvtropes-mcp are documented here.

## 0.2.0 — 2026-05-18

### Added
- **Scraper pipeline**: full BFS crawler with curl_cffi Chrome 131 impersonation,
  session warmup, Cloudflare block detection, gzip HTML cache, politeness delays
- **Ollama extraction**: async extraction pass via httpx, Qwen 2.5 structured
  JSON parsing, concurrent semaphore limit
- **LanceDB vector store**: pyarrow-schema table, nomic-embed-text embeddings,
  semantic_search MCP tool, merge_insert incremental updates
- **11 MCP tools** (later 12): trope_search (FTS5), trope_get, work_tropes,
  trope_examples, related_tropes, namespace_list, random_trope, scraper_status,
  trope_lookup_by_title, calibre_search, calibre_status, semantic_search
- **Calibre integration**: auto-discover metadata.db, book search by title/author,
  trope cross-reference via Literature/ namespace
- **React dashboard**: TropeSearch, WorkBrowser, TropeGraph, Chat, Log,
  Ollama config, Pages browser, Settings, Help — 10 pages
- **Cross-MCP bridge**: GET /api/lookup/title?hint=movie, GET /api/bridge
  fleet metadata, ?lookup= deep-link URL handling
- **Session warmup**: homepage fetch before first crawl to establish cookies
  and browsing context — eliminates Cloudflare blocks
- **Settings persistence**: data/settings.json with POST /api/settings,
  overrides env vars
- **CI**: GitHub Actions (ruff, pytest, biome, pre-commit), justfile,
  .pre-commit-config.yaml
- **63 unit + 28 e2e tests**, conftest fixtures with seeded DB

### Fixed
- Missing User-Agent header was causing all Cloudflare blocks — Chrome always
  sends UA, its absence is an instant bot signal
- Crawl visited.add() before fetch succeeded counted 404s as visited pages
- FTS5 virtual table UPSERT (DELETE + INSERT instead)
- LanceDB table creation (pyarrow schema, not tuple list)

### Changed
- curl_cffi impersonation: chrome120 → chrome131
- pyproject.toml: hatchling → setuptools (fleet standard)
- Main README: full cultural context, ethical scraping, legal analysis
- ARCHITECTURE.md: updated system diagram, data flow, schema

## 0.1.0 — 2026-05-04

### Added
- Project scaffold with docs/SCRAPER_PLAN.md (364 lines), ARCHITECTURE.md
- pyproject.toml with dependencies (curl_cffi, fastmcp, apscheduler, bs4)
- FastMCP 3.2 server stub with 8 tool placeholders
- FastAPI REST app with health/status/tools endpoints
- Vite+React+Tailwind dashboard scaffold
- Fleet-standard start.ps1/start.bat, uv.lock, .env.example, AGENTS.md
- Ports 10964/10965 registered in fleet WEBAPP_PORTS.md

### Status
- Scaffold only — implementation deferred pending robofang work

