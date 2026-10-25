# Configuration — tvtropes-mcp

All runtime settings come from environment variables with the `TVTROPES_MCP_`
prefix (see `src/tvtropes_mcp/config.py`, `Settings`). A `.env` file in the
repo root is loaded automatically. Copy `.env.example` to `.env` to start.

## Backend bind

| Variable | Default | Meaning |
|---|---|---|
| `TVTROPES_MCP_HOST` | `127.0.0.1` | FastAPI bind address (never `0.0.0.0` on a dev box) |
| `TVTROPES_MCP_PORT` | `10964` | Backend + MCP HTTP. Dashboard is `10965` (Vite / Tauri) |
| `TVTROPES_MCP_DATA_DIR` | `<repo>/data` | SQLite DB + scraper cache. Relative paths resolve against the repo root, never the CWD (Claude Desktop spawns stdio with `cwd=C:\Windows\System32`) |

## Ollama extraction

| Variable | Default | Meaning |
|---|---|---|
| `TVTROPES_MCP_OLLAMA_HOST` | `http://localhost:11434` | Extraction + embeddings endpoint |
| `TVTROPES_MCP_OLLAMA_MODEL` | `qwen2.5:27b` | Structured-extraction chat model |
| `TVTROPES_MCP_OLLAMA_TIMEOUT` | `120.0` | Seconds per extraction call |
| `TVTROPES_MCP_API_MODE` | `ollama` | `ollama` or `openai` (OpenAI-compatible `/v1` backends, e.g. LM Studio) |
| `TVTROPES_MCP_OPENAI_CHAT_MODEL` | `qwen/qwen3.6-27b` | Chat model in `openai` mode |
| `TVTROPES_MCP_OPENAI_EMBEDDING_MODEL` | `text-embedding-nomic-embed-text-v1.5` | Embedding model in `openai` mode |

## Scraper politeness

| Variable | Default | Meaning |
|---|---|---|
| `TVTROPES_MCP_SCRAPER_DELAY_MIN` | `8.0` | Minimum seconds between fetches |
| `TVTROPES_MCP_SCRAPER_DELAY_MAX` | `15.0` | Maximum seconds between fetches (randomized) |
| `TVTROPES_MCP_SCRAPER_DAILY_BUDGET` | `7000` | Max pages per day, then the crawler stops |
| `TVTROPES_MCP_OPENSERP_URL` | `http://127.0.0.1:7000` | `web_search` tool backend |

## Test-only

| Variable | Default | Meaning |
|---|---|---|
| `TVTROPES_MCP_AUTOSTART` | `1` | Set to `0` to skip crawler auto-start on import. `tests/conftest.py` sets this — a bare import must never start background work |

## User settings (persisted)

`data/settings.json` (via `POST /api/settings`) overrides env vars at runtime
for scraper delays/budget and the Ollama endpoint. The Settings page edits it.
Delete the file to fall back to env vars.
