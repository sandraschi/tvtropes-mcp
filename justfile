default_shell := "powershell.exe"

# ─── Python ────────────────────────────────────────────────────────
venv := ".venv\Scripts\python.exe"

test: _check-venv
    $(venv) -m pytest tests/ -v --tb=short

test-all: _check-venv
    $(venv) -m pytest tests/ -v --tb=long -x

lint: _check-venv
    ruff check src/ scraper/ tests/

format: _check-venv
    ruff format src/ scraper/ tests/

typecheck: _check-venv
    $(venv) -m mypy src/ --ignore-missing-imports

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
    cd web_sota && biome lint src/

web-fmt:
    cd web_sota && biome check --write src/

# ─── Housekeeping ──────────────────────────────────────────────────
_check-venv:
    if (-not (Test-Path ".venv")) { uv sync --extra dev }

pre-commit:
    pre-commit run --all-files

clean:
    Remove-Item -Recurse -Force .venv, __pycache__, .pytest_cache, .ruff_cache -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

.PHONY: test test-all lint format typecheck serve stdio scrape web web-build web-lint web-fmt pre-commit clean
