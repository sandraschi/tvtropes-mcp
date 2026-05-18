default_shell := "powershell.exe"

# ─── Python ────────────────────────────────────────────────────────
venv := ".venv\Scripts\python.exe"

test: _check-venv
    uv run python -m pytest tests/ -v --tb=short

test-all: _check-venv
    uv run python -m pytest tests/ -v --tb=long -x

lint: _check-venv
    uv run ruff check src/ scraper/ tests/

format: _check-venv
    uv run ruff format src/ scraper/ tests/

typecheck: _check-venv
    uv run python -m mypy src/ --ignore-missing-imports

# ─── Scraper ───────────────────────────────────────────────────────
serve: _check-venv
    uv run python -m tvtropes_mcp --serve

stdio: _check-venv
    uv run python -m tvtropes_mcp --stdio

scrape: _check-venv
    uv run python -m tvtropes_mcp --scrape

# ─── Frontend ──────────────────────────────────────────────────────
web:
    cd web_sota && npm run dev

web-build:
    cd web_sota && npm run build

web-lint:
    cd web_sota && npx biome lint src/

web-fmt:
    cd web_sota && npx biome check --write src/

web-ci:
    cd web_sota && npx biome ci src/

# ─── CI (matches .github/workflows/ci.yml) ────────────────────────────
ci: _check-venv lint format-check test web-ci web-build
    Write-Host "CI pipeline passed" -ForegroundColor Green

format-check: _check-venv
    uv run ruff format --check src/ scraper/ tests/

# ─── Housekeeping ──────────────────────────────────────────────────
_check-venv:
    if (-not (Test-Path ".venv")) { uv sync --extra dev }

pre-commit:
    uv run pre-commit run --all-files

clean:
    Remove-Item -Recurse -Force .venv, __pycache__, .pytest_cache, .ruff_cache -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

.PHONY: test test-all lint format format-check typecheck ci serve stdio scrape web web-build web-lint web-fmt web-ci pre-commit clean
