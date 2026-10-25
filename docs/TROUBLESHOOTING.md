# Troubleshooting — tvtropes-mcp

## Commit hooks fail on files you didn't touch

mypy follows imports and the Biome hook checks the whole `web_sota/src`
tree, so a partial stage can never go green. Stage the dependency-closed
set (leaves first: `scraper/*`, then `src/*`, then tests), or run
`pre-commit run --all-files` before `git add`. Never `--no-verify`.

## mypy: `ctx: Context = None` / implicit Optional

FastMCP passes `Context`, but tools are also called without one (tests,
REST proxy). Always annotate `ctx: Context | None = None`.

## mypy: `Row(label=, value=)` does not exist

`prefab_ui` 0.20 removed the kwargs form. Use `Metric(label=, value=)`
for key-value status cards.

## Biome hook fails with "could not determine executable to run"

Bare `npx` is not on PATH in non-interactive shells. The hook
(`scripts/pre-commit-biome.ps1`) resolves `node_modules/.bin/biome.cmd`
first, then `bunx`, then absolute-path `npx.cmd`. If you reinstall
node_modules, keep `.bin` on disk.

## Biome: `preset: "recommended"` is not a thing

Biome 2.x enables the recommended set with `"recommended": true` under
`linter.rules`. Tailwind v3 projects also need
`css.parser.tailwindDirectives: true` plus an override disabling
`suspicious/noUnknownAtRules` for `**/*.css`.

## Suppression comments that don't suppress

A `// biome-ignore <rule>:` comment only works when it is the trivia of
the node carrying the diagnostic — practically: immediately above that
node's own line. A comment above `<div` does not suppress a diagnostic
on its `dangerouslySetInnerHTML` attribute two lines down; move the
comment directly above the attribute. Get the rule name's exact case
from the diagnostic (`noDangerouslySetInnerHtml`, not `...HTML`).

## Tests start the crawler

`src/tvtropes_mcp/app.py` auto-starts the crawler on import. Tests set
`TVTROPES_MCP_AUTOSTART=0` in `tests/conftest.py`. If scraper tests fail
with "already running", the gate is missing, not the scraper.

## E2E scraper tests fail in sandboxes

`test_scraper_start_stop` needs no network, but anything hitting
`tvtropes.org` (sitemap fetch logs a 404 in offline sandboxes) is
environmental. Check for `HTTP 404 ... sitemap` in the log before
blaming the code.

## CRLF churn in diffs

`.gitattributes` forces LF. If your editor writes CRLF, Biome reflows
every line and the diff explodes. Set LF and re-save.

## Extraction returns 20/20 "Empty Ollama response"

`num_predict` caps **total** tokens **including the thinking trace** on
reasoning models (gemma4, qwen3, …). The extractor used to send
`options: {temperature: 0.1, num_predict: 2048}` with `format: "json"` —
thinking ate the whole budget and Ollama returned HTTP 200 with an empty
`response` string on every row. Bisected 2026-10-25: `temperature` alone is
harmless; any `num_predict` truncates (32 → 2 chars leak, 2048 → empty).
Fix: drop `num_predict` from extraction payloads (runaway length is bounded
by the 120 s client timeout, not a cap that starves the answer). If you
change the extraction model, re-run one page through `extract_page`
directly and check `len(response)` before a full pass.

## Dashboard shows stale tool counts

`manifest.json`, `glama.json`, the Dashboard hero, and
`tests/test_e2e.py::test_tools_list` hardcode the tool list. The source
of truth is `mcp.list_tools()` (also `GET /api/capabilities`). Update
all four when adding a tool.
