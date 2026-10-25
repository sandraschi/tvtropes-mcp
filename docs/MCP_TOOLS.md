# MCP Tools Reference

17 tools are registered via `@mcp.tool` in [`src/tvtropes_mcp/server.py`](../src/tvtropes_mcp/server.py). Fifteen query the local SQLite mirror/LanceDB; `web_search` queries the web via OpenSERP and `show_status_card` renders a Prefab card. Every tool is annotated `readOnlyHint`.

## Tool List

| Tool | Args | Description |
|------|------|-------------|
| `trope_search` | `query`, `limit` | Full-text FTS5 search across all trope names and descriptions |
| `trope_get` | `trope_id` | Full trope page: description, laconic, examples, sub/super/sister/related |
| `work_tropes` | `work_id` | All tropes for a work (e.g. `Series/BreakingBad`) |
| `trope_examples` | `trope_id`, `namespace?`, `limit` | Examples filtered by medium (Film, Anime...) |
| `related_tropes` | `trope_id` | Graph traversal: SubTrope, SuperTrope, SisterTrope, Related |
| `namespace_list` | — | All namespaces with page counts |
| `random_trope` | — | Random trope weighted by example count |
| `scraper_status` | — | Crawl progress, DB size, Ollama backlog |
| `semantic_search` | `query`, `limit` | Vector similarity via LanceDB + Ollama embeddings |
| `trope_lookup_by_title` | `title` | Cross-reference book title against Literature/ |
| `calibre_search` | `title?`, `author?`, `limit` | Search local Calibre library |
| `calibre_status` | — | Check Calibre library detection |
| `web_search` | `query`, `engine?`, `limit?` | Search the web for trope context via OpenSERP (requires local openserp on :7000) |
| `works_in_namespace` | `namespace`, `limit`, `offset` | Browse works by medium |
| `show_status_card` | — | Prefab scraper/database status card |
| `trope_agentic_assist` | `goal` | Multi-step research plan via MCP sampling |
| `vector_status` | — | LanceDB vector count plus rebuild job states |

## CLI Usage

```powershell
uv run python -m tvtropes_mcp --stdio
# Then in any MCP client:
# trope_search("villain redemption", limit=5)
# trope_get("Main/ChekhovsGun")
# work_tropes("Series/NeonGenesisEvangelion")
# related_tropes("Main/FiveManBand")
```

## REST Proxy

```powershell
curl -X POST http://127.0.0.1:10964/api/mcp/tool \
  -H "Content-Type: application/json" \
  -d '{"name": "trope_search", "args": {"query": "time loop", "limit": 3}}'

curl -X POST http://127.0.0.1:10964/api/mcp/tool \
  -H "Content-Type: application/json" \
  -d '{"name": "trope_get", "args": {"trope_id": "Main/ChekhovsGun"}}'
```

## CLI Flags

| Flag | Transport | Use case |
|------|-----------|----------|
| `--serve` | Streamable HTTP (SSE) | FastAPI + MCP on :10964 |
| `--stdio` | stdio | Claude Desktop, Cursor |
| `--scrape` | — | Standalone scraper daemon |
| `--debug` | — | Verbose logging to stderr |
