# Tools — tvtropes-mcp (16 MCP tools)

Registered in `src/tvtropes_mcp/server.py`. Every tool returns
`{"success": true, ...}` plus a `message` string on completion or a
`{"success": false, "error": ...}` dict — never a bare exception.
`GET /api/capabilities` exposes the same list to webapps and agents.

## Search & discovery

| Tool | Args | What |
|---|---|---|
| `trope_search` | `query`, `limit` (≤100) | Full-text FTS5 search over trope names + descriptions |
| `trope_get` | `trope_id` (`Main/ChekhovsGun`) | Full trope page: description, sub/super/sister/related, examples |
| `trope_examples` | `trope_id`, `namespace?`, `limit` | Examples filtered by medium |
| `related_tropes` | `trope_id` | Traverse the trope relationship graph |
| `semantic_search` | `query`, `limit` | Vector similarity via LanceDB (`nomic-embed-text`) |
| `random_trope` | — | Random trope weighted by example count |
| `web_search` | `query`, `engine`, `limit` | OpenSERP web search for context outside the mirror |

## Works & namespaces

| Tool | Args | What |
|---|---|---|
| `work_tropes` | `work_id` (`Series/BreakingBad`) | All tropes for one work |
| `works_in_namespace` | `namespace`, `limit`, `offset` | Browse works by medium |
| `namespace_list` | — | All namespaces with page counts |
| `trope_lookup_by_title` | `title` | Cross-reference a book title against `Literature/` |
| `trope_agentic_assist` | `goal` | Multi-step research plan via MCP sampling |
| `show_status_card` | — | Prefab status card (app=True) |

## External & system

| Tool | Args | What |
|---|---|---|
| `calibre_search` | `title`, `author`, `limit` | Search the local Calibre library |
| `calibre_status` | — | Calibre library detection state |
| `scraper_status` | — | Crawl progress, DB size, extraction backlog |

## REST mirrors

`POST /api/mcp/tool` (`{"name", "args"}`) proxies any tool for the dashboard
Chat page; `GET /api/mcp/tools` lists schemas; `GET /api/tools` lists names.
