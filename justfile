import 'scripts/just/fleet.just'

default_shell := "powershell.exe"

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# ── Quality ────────────────────────────────────────────────────────

# Ruff lint Python source
lint:
    uv run ruff check src/ scraper/ tests/

# Ruff format Python source
format:
    uv run ruff format src/ scraper/ tests/

# Ruff format check (CI mode, read-only)
format-check:
    uv run ruff format --check src/ scraper/ tests/

# Run Python tests
test:
    uv run python -m pytest tests/ -v --tb=short

# Run tests verbosely, stop on first failure
test-all:
    uv run python -m pytest tests/ -v --tb=long -x

# Biome lint frontend
web-lint:
    cd web_sota && npx biome lint src/

# Biome auto-fix frontend
web-fmt:
    cd web_sota && npx biome check --write src/

# Biome CI check frontend
web-ci:
    cd web_sota && npx biome ci src/

# Build frontend
web-build:
    cd web_sota && npm run build

# Full CI pipeline (matches .github/workflows/ci.yml)
ci: lint format-check test web-ci web-build
    Write-Host "CI pipeline passed" -ForegroundColor Green

# ── Serving ────────────────────────────────────────────────────────

# Start API + MCP HTTP on :10964
serve:
    uv run python -m tvtropes_mcp --serve

# MCP over stdio (Claude Desktop, Cursor)
stdio:
    uv run python -m tvtropes_mcp --stdio

# Standalone crawler daemon
scrape:
    uv run python -m tvtropes_mcp --scrape

# Start React dashboard on :10965
web:
    cd web_sota && npm run dev

# Start full stack (backend + frontend via web_sota/start.ps1)
dev:
    cd web_sota && .\start.ps1

# ── Install ────────────────────────────────────────────────────────

# Full install: Python deps + frontend deps. Run after git clone.
install:
    uv sync --extra dev
    if (Test-Path web_sota) { Push-Location web_sota; npm install; Pop-Location }
    Write-Host "Install complete. Run: just serve" -ForegroundColor Green

# Sync Python deps only
sync:
    uv sync --extra dev

# Install frontend deps only
sync-web:
    cd web_sota && npm install

# ── Repo-specific ──────────────────────────────────────────────────

# Resolve a title to a TVTropes page path
lookup title="The Matrix" hint="movie":
    curl -s "http://127.0.0.1:10964/api/lookup/title?title={{title}}&hint={{hint}}" | ConvertFrom-Json | ConvertTo-Json

# Crawl from a starting URL with depth limit
crawl url="VisualNovel/Planetarian" depth="1":
    curl -s -X POST http://127.0.0.1:10964/api/scraper/crawl -H "Content-Type: application/json" -d '{"url": "{{url}}", "depth": {{depth}}}' | ConvertFrom-Json | ConvertTo-Json

# Check scraper status
scraper-status:
    curl -s http://127.0.0.1:10964/api/scraper/status | ConvertFrom-Json | ConvertTo-Json

# Check Ollama/LMStudio connection
ollama-status:
    curl -s http://127.0.0.1:10964/api/ollama/status | ConvertFrom-Json | ConvertTo-Json

# Get fleet bridge metadata
bridge:
    curl -s http://127.0.0.1:10964/api/bridge | ConvertFrom-Json | ConvertTo-Json

# Call any MCP tool via REST proxy
mcp name="scraper_status" args="{}":
    curl -s -X POST http://127.0.0.1:10964/api/mcp/tool -H "Content-Type: application/json" -d '{"name": "{{name}}", "args": {{args}}}' | ConvertFrom-Json | ConvertTo-Json

# ── MCP Client Install ────────────────────────────────────────────

# Install into an MCP client config: claude|cursor|windsurf|zed|antigravity|lmstudio|code|print
install-mcp client="print":
    .\install-mcp.ps1 {{client}}

# Pack MCPB bundle (creates dist/tvtropes-mcp-v{version}.mcpb)
mcpb-pack:
    $ver = (Get-Content pyproject.toml | Select-String '^version = "(.*)"' | ForEach-Object { $$_.Matches.Groups[1].Value }); \
    $null = New-Item -ItemType Directory -Path dist -Force; \
    Compress-Archive -Path manifest.json, llms.txt, llms-full.txt, glama.json, src, scraper, docs, pyproject.toml, uv.lock -DestinationPath "dist/tvtropes-mcp-v$ver.mcpb" -CompressionLevel Optimal -Force; \
    Write-Host "Created dist/tvtropes-mcp-v$ver.mcpb" -ForegroundColor Green

# Create a SQLite backup snapshot
backup:
    curl -s -X POST http://127.0.0.1:10964/api/scraper/backup | ConvertFrom-Json | ConvertTo-Json

# ── Housekeeping ──────────────────────────────────────────────────

# Run pre-commit on all files
pre-commit:
    uv run pre-commit run --all-files

# Clean generated files
clean:
    Remove-Item -Recurse -Force .venv, __pycache__, .pytest_cache, .ruff_cache, web_sota/node_modules -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

# ── Tauri Native ───────────────────────────────────────────────────────────────

# Build Tauri native desktop app (full pipeline: frontend + backend)
build-native:
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npx @tauri-apps/cli build

# Run the CUA smoke test against the installed NSIS app
cua-nsis-test:
    uv run python scripts/cua-smoke.py
