# Installation

## 🚀 Quick Start (recommended)

```powershell
# Install just if you don't have it
winget install Casey.Just    # Windows
# scoop install just          # Windows (alternative)
# brew install just           # macOS
# sudo apt install just       # Debian/Ubuntu
# cargo install just          # Linux (Rust)

git clone https://github.com/sandraschi/tvtropes-mcp
cd tvtropes-mcp
just
```

The interactive recipe dashboard opens in your browser. From there:

```powershell
just bootstrap   # install all dependencies
just serve       # start the server
just web         # start the frontend (if applicable)
```

> **Why not `pip install`?** MCP servers bundle webapps, configs, project scaffolding, and tooling that a flat Python package can't deliver. PyPI offers no safety advantage — it doesn't audit packages either. `just` gives you the complete, ready-to-run stack.

---

## 🐌 Traditional Setup

If you prefer not to use `just`:

1. Install [Python 3.13+](https://python.org) and [uv](https://docs.astral.sh/uv/)
2. Clone and enter the repo:
   ```powershell
   git clone https://github.com/sandraschi/tvtropes-mcp
   cd tvtropes-mcp
   ```
3. Install dependencies:
   ```powershell
   uv sync --all-extras
   ```
4. Start the server:
   ```powershell
   # stdio mode (for MCP clients like Claude Desktop)
   uv run python -m tvtropes_mcp.server

   # HTTP mode (for web dashboard)
   uv run uvicorn tvtropes_mcp.server:app --port 10964
   ```
5. Open `http://localhost:10964` or the frontend URL.

---

## ❓ Troubleshooting

| Issue | Fix |
|---|---|
| `just` not found | Install via `winget install Casey.Just`, `scoop install just`, or `brew install just` |
| Port conflict | Run `just kill-all` to clear fleet ports (10700–11000) |
| Dependencies out of sync | `uv sync --all-extras` |
| Something else | [Open a GitHub issue](https://github.com/sandraschi/tvtropes-mcp/issues) |

---

*See the main [README](README.md) for feature overview and documentation.

---

## Legacy Documentation

_This INSTALL.md was updated with the standard fleet Quick Start template. The original instructions are preserved below._

# Installation Guide

## Prerequisites

| Dependency | Version | Required for |
|------------|---------|-------------|
| **Python** | 3.11+ | Server, scraper, all Python tools |
| **uv** | latest | Python package management (replaces pip) |
| **Node.js** | 18+ | React dashboard |
| **Ollama** | latest (optional) | Structured trope extraction + semantic embeddings |

### Installing Python + uv

```powershell
# Install uv (if not already installed)
winget install --id=astral-sh.uv

# Verify
uv --version
python --version  # must be 3.11+
```

### Installing Node.js

```powershell
# Install Node.js LTS
winget install --id=OpenJS.NodeJS.LTS

# Verify
node --version  # must be 18+
npm --version
```

### Installing Ollama (optional)

```powershell
# Download from https://ollama.com or:
winget install --id=Ollama.Ollama

# Pull recommended models
ollama pull qwen2.5:27b      # structured extraction
ollama pull nomic-embed-text  # semantic search embeddings
```

---

## Clone & Install

```powershell
# Clone
git clone https://github.com/sandraschi/tvtropes-mcp.git
cd tvtropes-mcp

# Full install (Python deps + frontend deps)
uv sync --extra dev
cd web_sota && npm install && cd ..

# Or use the justfile:
just install
```

---

## Configuration

### Environment Variables

Create `.env` in the project root (or set these in your shell):

```ini
# Server bind
TVTROPES_MCP_HOST=127.0.0.1
TVTROPES_MCP_PORT=10964

# Data storage (SQLite DB + cache live here)
TVTROPES_MCP_DATA_DIR=data

# Ollama endpoint
TVTROPES_MCP_OLLAMA_HOST=http://localhost:11434
TVTROPES_MCP_OLLAMA_MODEL=qwen2.5:27b
```

### User Settings (UI-configurable)

Once the server is running, settings can be changed from the **Settings** page in the dashboard or via the API. These persist to `data/settings.json` and override environment variables:

- Ollama host URL
- Ollama model name
- Extraction timeout
- Scraper min/max delay
- Daily crawl budget

---

## Start

### Backend (API + MCP)

```powershell
uv run python -m tvtropes_mcp --serve
# ÔåÆ http://127.0.0.1:10964
# ÔåÆ MCP SSE at http://127.0.0.1:10964/mcp
# ÔåÆ REST at http://127.0.0.1:10964/api
```

### Dashboard (separate terminal)

```powershell
cd web_sota
npm run dev
# ÔåÆ http://127.0.0.1:10965
```

### Single command (both backend + dashboard)

```powershell
just dev
# Or start from the root:
.\start.ps1
```

---

## Verify It Works

```powershell
# Health check
curl http://127.0.0.1:10964/api/health
# ÔåÆ {"status":"ok","service":"tvtropes-mcp"}

# List MCP tools
curl http://127.0.0.1:10964/api/tools

# Crawl a test page
curl -X POST http://127.0.0.1:10964/api/scraper/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "VisualNovel/Planetarian", "depth": 1}'
```

---

## MCP Client Setup

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tvtropes-mcp": {
      "command": "uv",
      "args": ["run", "--project", "C:\\path\\to\\tvtropes-mcp", "python", "-m", "tvtropes_mcp", "--stdio"]
    }
  }
}
```

### Cursor

In Cursor settings ÔåÆ MCP Servers ÔåÆ Add:

```
Name: tvtropes-mcp
Type: command
Command: uv run --project C:\path\to\tvtropes-mcp python -m tvtropes_mcp --stdio
```

---

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `Connection refused` on :10964 | Backend not started ÔÇö run `just serve` |
| Dashboard shows "API not reachable" | Backend not running, or wrong port |
| Crawl returns 0 URLs | Page may not exist on TVTropes (check namespace) |
| Cloudflare block | Session warmup should handle this; if persistent, Cloudflare may have escalated protection |
| Ollama extraction not working | Run `just ollama-status` to check connectivity |
| `uv` command not found | Install via winget or astral.sh |
