# Development — tvtropes-mcp

## Prereqs

- Python 3.13, [`uv`](https://docs.astral.sh/uv/) (full path:
  `C:\Users\sandr\.local\bin\uv.exe` — never naked `uv`)
- Node via `C:\Program Files\nodejs` + `C:\Users\sandr\.bun\bin\bun.exe`
- `just` (`C:\Users\sandr\.local\bin\just.exe`), `git`
  (`C:\Program Files\Git\cmd\git.exe`)

## Setup

```powershell
uv sync
uv run pre-commit install   # hooks are gates, not suggestions
cd web_sota; npm install; cd ..
```

## Daily loop

| Task | Command |
|---|---|
| Serve (HTTP + MCP on 10964) | `just serve` |
| Stdio (Claude Desktop) | `just` default / `uv run python -m tvtropes_mcp --stdio` |
| Scraper daemon only | `uv run python -m tvtropes_mcp --scrape` |
| Lint | `just lint` (`ruff check`) |
| Format | `just fmt` (`ruff format`) |
| Typecheck | pre-commit `mypy` hook (`--ignore-missing-imports`) |
| Tests | `just test` (fast) / `just test-all` / `just e2e` |
| Full gate | `just ci` (ruff + format-check + pytest + biome + web build) |
| Frontend dev | `just web-dev` (Vite on 10965, proxies `/api` to 10964) |

## Commit hooks (all must pass — never `--no-verify`)

`ruff`, `ruff-format`, `mypy`, `trailing-whitespace`, `end-of-file-fixer`,
`biome ci (web_sota)` via `scripts/pre-commit-biome.ps1`
(which resolves `node_modules/.bin/biome.cmd` — bare `npx` is not on PATH
in non-interactive shells).

**Batch rule for commits:** mypy follows imports, and the Biome hook checks
the whole `web_sota/src` tree, so a commit's staged set must be the
**dependency-closed green set** (leaves first, importers after). A partial
stage can never pass the hooks. When in doubt, verify with
`git stash -q && pre-commit run --all-files && git stash pop -q`
before pushing. Max 5 files per commit for reviewability; hook-atomic
closures that exceed it must say so in the message.

## Tests

`tests/conftest.py` builds a fresh `TestClient` on a temp DB and sets
`TVTROPES_MCP_AUTOSTART=0` — the app auto-starts the crawler on import,
which would otherwise leak background work into every test session.
`test_e2e.py` asserts the live tool count (16); bump it when adding tools.

## Line endings

`.gitattributes` forces LF (`* text=auto eol=lf`). Do not commit CRLF —
Biome's formatter diffs every CRLF line and `biome ci` fails.
