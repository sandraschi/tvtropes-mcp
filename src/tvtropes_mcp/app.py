"""FastAPI: REST dashboard API + mounted FastMCP HTTP (streamable)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, FastAPI

from tvtropes_mcp.config import load_settings
from tvtropes_mcp.db import (
    ensure_db,
)
from tvtropes_mcp.db import (
    scraper_status as db_scraper_status,
)
from tvtropes_mcp.log_ring import install_log_ring
from tvtropes_mcp.scraper_manager import ScraperManager
from tvtropes_mcp.server import mcp

install_log_ring()

log = logging.getLogger(__name__)

_settings = load_settings()
_db_path = str(_settings.resolved_data_dir() / "tvtropes.db")
ensure_db(_db_path)

mcp_http = mcp.http_app(path="/mcp")
router = APIRouter(prefix="/api")

_scraper = ScraperManager(_db_path)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "tvtropes-mcp"}


@router.get("/status")
async def api_status() -> dict[str, Any]:
    stats = db_scraper_status(db_path=_db_path)
    mgr = _scraper.get_status()
    stats["scraper"] = {
        "state": "running" if mgr.get("crawler", {}).get("running") else "stopped",
        **mgr.get("crawler", {}).get("crawl", {}),
    }
    return stats


@router.post("/scraper/start")
async def api_scraper_start() -> dict[str, Any]:
    return _scraper.start_crawler()


@router.post("/scraper/stop")
async def api_scraper_stop() -> dict[str, Any]:
    return _scraper.stop_crawler()


@router.get("/scraper/status")
async def api_scraper_status() -> dict[str, Any]:
    return _scraper.get_status()


@router.post("/scraper/extract")
async def api_scraper_extract() -> dict[str, Any]:
    result = await _scraper.run_extraction_pass()
    return result


@router.post("/scraper/bootstrap")
async def api_scraper_bootstrap() -> dict[str, Any]:
    from scraper.bootstrap import run_bootstrap

    result = run_bootstrap(_db_path)
    return result


@router.post("/scraper/crawl")
async def api_scraper_crawl(body: dict[str, Any]) -> dict[str, Any]:
    """Crawl from a starting URL with depth limit.

    Accepts a full TVTropes URL or a short path like "Anime/Planetarian".
    Depth controls how many link-hops to follow (default 1 = only direct links).
    Runs the synchronous crawler in a thread to avoid blocking the event loop.
    """

    from bs4 import BeautifulSoup

    from scraper.crawler import TvtropesCrawler
    from scraper.db import load_config, queue_urls
    from scraper.parser import TVTROPES_BASE, classify_url, extract_page_links, extract_page_title

    raw = body.get("url", "").strip()
    depth = max(1, min(int(body.get("depth", 1)), 3))
    loop = asyncio.get_running_loop()

    if not raw:
        return {"success": False, "error": "Missing url"}

    if "/" in raw and not raw.startswith("http"):
        raw = f"{TVTROPES_BASE}/pmwiki/pmwiki.php/{raw}"
    elif not raw.startswith("http"):
        raw = f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/{raw}"

    classified = classify_url(raw)
    if not classified:
        return {"success": False, "error": f"Invalid TVTropes URL: {raw}"}

    config = load_config()
    crawler = TvtropesCrawler(config)
    visited: set[str] = set()
    queued = 0
    errors = 0
    page_title: str | None = None
    sample_links: list[dict[str, str]] = []
    links_found = 0

    try:
        current_level = {raw}
        for level in range(depth):
            log.info(f"Crawl level {level + 1}/{depth}: {len(current_level)} pages")
            next_level: set[str] = set()
            for url in current_level:
                if url in visited:
                    continue
                result = await loop.run_in_executor(None, crawler.fetch, url)
                if not result["success"]:
                    reason = result.get("error", "unknown")
                    log.warning(f"Failed to fetch {url}: {reason}")
                    if result.get("blocked"):
                        errors += 1
                    continue
                visited.add(url)
                if not result.get("html"):
                    continue
                soup = BeautifulSoup(result["html"], "lxml")
                if level == 0:
                    page_title = extract_page_title(soup)
                links = extract_page_links(soup, url)
                if level + 1 < depth:
                    for lnk in links:
                        if lnk["url"] not in visited:
                            next_level.add(lnk["url"])
                entries = [lnk for lnk in links if lnk["url"] not in visited]
                if entries:
                    links_found += len(entries)
                    if len(sample_links) < 10:
                        sample_links.extend(
                            {"ns": e["namespace"], "name": e["page_name"]}
                            for e in entries[: 10 - len(sample_links)]
                        )
                    added = await loop.run_in_executor(
                        None, lambda e=entries: queue_urls(_db_path, e),
                    )
                    queued += added
                await asyncio.sleep(1)
            current_level = next_level
            if not current_level:
                break
    except Exception as e:
        log.error(f"Crawl error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "starting_url": raw,
            "pages_visited": len(visited),
            "urls_queued": queued,
        }
    finally:
        await loop.run_in_executor(None, crawler.close)

    next_steps: list[str] = []
    if queued > 0:
        next_steps.append(f"{queued} URLs queued for scraping.")
        if not _scraper.crawler_running:
            start_result = _scraper.start_crawler()
            if start_result.get("success"):
                next_steps.append("Background scraper auto-started to fetch these pages.")

    result = {
        "success": True,
        "starting_url": raw,
        "namespace": classified[0],
        "page_name": classified[1],
        "page_title": page_title,
        "depth": depth,
        "pages_visited": len(visited),
        "urls_queued": queued,
        "links_found": links_found,
        "errors": errors,
        "sample_links": sample_links,
        "next_steps": next_steps,
    }

    if visited and visited == {raw} and errors > 0:
        result["note"] = (
            "The starting page was blocked by Cloudflare. The scraper will "
            "back off and retry; this is rare with the current configuration."
        )
    elif queued == 0 and visited:
        result["note"] = "Page was fetched but no internal links were found to queue."

    return result


@router.get("/settings")
async def api_settings() -> dict[str, Any]:
    """Return current runtime settings (safe values only)."""
    from tvtropes_mcp.config import load_settings as _ls

    s = _ls()
    return {
        "host": s.host,
        "port": s.port,
        "data_dir": str(s.resolved_data_dir()),
        "ollama_host": s.ollama_host,
        "ollama_model": s.ollama_model,
        "ollama_timeout": s.ollama_timeout,
        "scraper_delay_min": s.scraper_delay_min,
        "scraper_delay_max": s.scraper_delay_max,
        "scraper_daily_budget": s.scraper_daily_budget,
    }


@router.get("/ollama/status")
async def api_ollama_status() -> dict[str, Any]:
    """Check if Ollama (or LMStudio) is running and has the configured model."""
    import httpx

    s = load_settings()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{s.ollama_host}/api/tags")
            if r.status_code == 200:
                models = r.json().get("models", [])
                model_names = [m["name"] for m in models]
                configured_found = any(m.startswith(s.ollama_model) for m in model_names)
                return {
                    "running": True,
                    "host": s.ollama_host,
                    "model_configured": s.ollama_model,
                    "model_found": configured_found,
                    "models_available": model_names,
                }
            return {"running": False, "host": s.ollama_host, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"running": False, "host": s.ollama_host, "error": str(e)}


@router.get("/log")
async def api_log(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent log entries from the scraper."""
    from tvtropes_mcp.log_ring import get_recent

    return get_recent(limit=limit)


@router.get("/pages")
async def api_pages(
    status: str | None = None,
    namespace: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List crawled pages with optional status/namespace filter."""
    from scraper.db import get_conn

    where = "1=1"
    params: list[Any] = []
    if status:
        where += " AND status=?"
        params.append(status)
    if namespace:
        where += " AND namespace=?"
        params.append(namespace)

    with get_conn(_db_path) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM pages WHERE {where}", params  # noqa: S608
        ).fetchone()[0]
        cols = "id, url, namespace, page_name, status, crawled_at, http_status, blocked, retry_count"
        rows = conn.execute(
            f"SELECT {cols} FROM pages WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?",  # noqa: S608
            [*params, limit, offset],
        ).fetchall()
        return {
            "total": total,
            "pages": [dict(r) for r in rows],
            "limit": limit,
            "offset": offset,
        }


@router.get("/pages/{page_id}/content")
async def api_page_content(page_id: int) -> dict[str, Any]:
    """Return the main body content of a crawled page from its cached HTML."""
    from scraper.db import get_conn, load_config
    from tvtropes_mcp.content_extractor import extract_main_content, extract_text_only

    with get_conn(_db_path) as conn:
        row = conn.execute(
            "SELECT url, content_hash FROM pages WHERE id=?", (page_id,)
        ).fetchone()
    if not row:
        return {"error": "Page not found"}

    content_hash = row["content_hash"]
    if not content_hash:
        return {"error": "No cached HTML for this page (not yet crawled)"}

    from scraper.crawler import TvtropesCrawler

    config = load_config()
    crawler = TvtropesCrawler(config)
    try:
        html = crawler.read_cached_html(content_hash)
    finally:
        crawler.close()

    if not html:
        return {"error": "Cached HTML file not found on disk"}

    main_html = extract_main_content(html)
    text = extract_text_only(html)
    return {
        "url": row["url"],
        "content_hash": content_hash,
        "main_html": main_html,
        "text": text,
        "html_size": len(html),
        "main_size": len(main_html),
    }


@router.get("/vector/count")
async def api_vector_count() -> dict[str, Any]:
    """Return the number of vectors in the LanceDB index."""
    from tvtropes_mcp.vector_store import count_vectors

    return {"count": count_vectors(_settings.resolved_data_dir())}


@router.post("/vector/rebuild")
async def api_vector_rebuild() -> dict[str, Any]:
    """Rebuild the LanceDB vector index from all tropes in the SQLite DB."""
    from scraper.db import get_conn
    from tvtropes_mcp.vector_store import upsert_trope_embedding

    embedded = 0
    errors = 0
    with get_conn(_db_path) as conn:
        rows = conn.execute(
            "SELECT namespace, page_name, title, description, laconic FROM tropes"
        ).fetchall()
    for row in rows:
        trope = dict(row)
        ok = await upsert_trope_embedding(
            _settings.resolved_data_dir(),
            trope,
            ollama_host=_settings.ollama_host,
        )
        if ok:
            embedded += 1
        else:
            errors += 1
    return {"success": True, "embedded": embedded, "errors": errors, "total": embedded + errors}


@router.get("/tools")
async def api_tools() -> dict[str, Any]:
    return {
        "tools": [
            "trope_search",
            "trope_get",
            "work_tropes",
            "trope_examples",
            "related_tropes",
            "namespace_list",
            "random_trope",
            "scraper_status",
            "trope_lookup_by_title",
            "calibre_search",
            "calibre_status",
            "semantic_search",
        ],
        "mcp_http_path": "/mcp",
    }


@router.get("/calibre/status")
async def api_calibre_status() -> dict[str, Any]:
    from tvtropes_mcp.calibre_ops import calibre_status as _cs

    return _cs()


@router.get("/calibre/search")
async def api_calibre_search(
    title: str | None = None,
    author: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    from tvtropes_mcp.calibre_ops import find_calibre_db, search_books

    calibre_db = find_calibre_db()
    if calibre_db is None:
        return {"found": False, "books": [], "total": 0}
    books = search_books(title=title, author=author, limit=limit, calibre_db=calibre_db)
    return {"found": True, "books": books, "total": len(books)}


@router.post("/mcp/tool")
async def api_mcp_tool(body: dict[str, Any]) -> dict[str, Any]:
    """Proxy: call an MCP tool by name and return its result as JSON."""
    import json

    from fastmcp.exceptions import NotFoundError

    from tvtropes_mcp.server import mcp

    name = body.get("name", "")
    args = body.get("args", {})
    if not name:
        return {"success": False, "error": "Missing tool name"}
    try:
        result = await mcp.call_tool(name, args)
    except NotFoundError:
        return {"success": False, "error": f"Unknown tool: {name!r}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    if result.content:
        text = result.content[0].text
        return json.loads(text)
    return {"success": False, "error": "No content returned"}


@router.get("/mcp/tools")
async def api_mcp_tools_list() -> list[dict[str, Any]]:
    """Proxy: list all registered MCP tools with their schemas."""
    from tvtropes_mcp.server import mcp

    tools = await mcp.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description,
            "inputSchema": getattr(t, "inputSchema", getattr(t, "input_model_json", None)),
        }
        for t in tools
    ]


def build_app() -> FastAPI:
    settings = load_settings()
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="tvtropes-mcp",
        version="0.2.0",
        lifespan=mcp_http.lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.mount("/mcp", mcp_http)

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "service": "tvtropes-mcp",
            "version": "0.2.0",
            "transports": {
                "stdio": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "tvtropes_mcp", "--stdio"],
                },
                "streamable_http": {
                    "mcp_url": f"http://{settings.host}:{settings.port}/mcp",
                },
            },
            "mcp_http": f"http://{settings.host}:{settings.port}/mcp",
            "api": f"http://{settings.host}:{settings.port}/api",
            "webapp": "http://127.0.0.1:10965",
        }

    @app.get("/.well-known/mcp/manifest.json")
    async def well_known_mcp_manifest() -> dict[str, Any]:
        s = load_settings()
        base = f"http://{s.host}:{s.port}"
        return {
            "name": "tvtropes-mcp",
            "version": "0.2.0",
            "repository": "https://github.com/sandraschi/tvtropes-mcp",
            "transports": {
                "stdio": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "tvtropes_mcp", "--stdio"],
                },
                "streamable_http": {
                    "url": f"{base}/mcp",
                    "note": "FastMCP 3.2 http_app; start with: uv run python -m tvtropes_mcp --serve",
                },
            },
        }

    return app


app = build_app()
