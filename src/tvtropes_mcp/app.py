"""FastAPI: REST dashboard API + mounted FastMCP HTTP (streamable)."""

from __future__ import annotations

import asyncio
import json as _json
import logging
import time
from typing import Any

from fastapi import APIRouter, FastAPI, Request

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

mcp_http = mcp.http_app(path="/")
router = APIRouter(prefix="/api")

_scraper = ScraperManager(_db_path)
_start_time = time.time()

# Auto-start crawler on service boot so the mirror is always being populated.
_res = _scraper.start_crawler()
if _res.get("success"):
    log.info("Crawler auto-started: %s", _res.get("message"))
else:
    log.info("Crawler auto-start: %s", _res.get("message"))


@router.get("/health")
async def health() -> dict[str, Any]:
    from tvtropes_mcp.server import mcp as _mcp

    tools = await _mcp.list_tools()
    scraper_running = _scraper.get_status().get("crawler", {}).get("running", False)
    return {
        "status": "ok",
        "service": "tvtropes-mcp",
        "version": "0.2.0",
        "uptime_seconds": int(time.time() - _start_time),
        "tool_count": len(tools),
        "providers": {
            "scraper": f"scraper:{'running' if scraper_running else 'stopped'}",
            "ollama": f"{_settings.ollama_host}/{_settings.ollama_model}",
        },
    }


@router.get("/v1/diagnostics")
async def api_diagnostics() -> dict[str, Any]:
    import platform as _platform
    import shutil as _shutil

    from tvtropes_mcp.server import mcp as _mcp

    tools = await _mcp.list_tools()
    tools_list = [{"name": t.name, "description": t.description} for t in tools]
    disk = _shutil.disk_usage(_settings.resolved_data_dir())

    return {
        "status": "ok",
        "server": "tvtropes-mcp",
        "version": "0.2.0",
        "uptime_seconds": int(time.time() - _start_time),
        "tool_count": len(tools),
        "tools": tools_list,
        "system": {
            "windows": True,
            "cpu_count": getattr(_platform, "cpu_count", lambda: 0)(),
            "disk_free_gb": round(disk.free / (1024**3), 1),
        },
        "errors": [],
    }


@router.get("/status")
async def api_status() -> dict[str, Any]:
    stats = db_scraper_status(db_path=_db_path)
    mgr = _scraper.get_status()
    crawler = mgr.get("crawler", {})
    stats["scraper"] = {
        "state": "running" if crawler.get("running") else "stopped",
        "current_url": crawler.get("current_url", ""),
        "pages_crawled_this_session": crawler.get("pages_crawled_this_session", 0),
        **crawler.get("crawl", {}),
    }
    stats["extractor"] = mgr.get("extractor", {"running": False})
    return stats


@router.get("/events")
async def api_events(request: Request):
    """SSE endpoint — streams crawl/extraction events for live dashboard updates."""
    from fastapi.responses import StreamingResponse

    async def event_stream():
        last_status = ""
        while True:
            if await request.is_disconnected():
                break
            mgr = _scraper.get_status()
            crawler = mgr.get("crawler", {})
            crawl = crawler.get("crawl", {})
            url = crawler.get("current_url", "")
            status_line = f"{crawler.get('running')}|{crawl.get('crawled',0)}|{crawl.get('pending',0)}|{crawl.get('extracted',0)}|{url}"
            if status_line != last_status:
                last_status = status_line
                data = _json.dumps({
                    "crawler_running": crawler.get("running"),
                    "extractor_running": mgr.get("extractor", {}).get("running"),
                    "current_url": url,
                    "crawled": crawl.get("crawled", 0),
                    "pending": crawl.get("pending", 0),
                    "extracted": crawl.get("extracted", 0),
                    "daily": crawl.get("daily", 0),
                })
                yield f"data: {data}\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/shutdown")
async def api_shutdown() -> dict[str, Any]:
    """Gracefully stop the scraper and shut down the server."""
    _scraper.stop_crawler()
    import asyncio
    asyncio.get_event_loop().stop()
    return {"success": True, "message": "Shutting down"}


@router.post("/restart")
async def api_restart() -> dict[str, Any]:
    """Restart the NSSM service in the background.

    Spawns a fire-and-forget thread that waits 1s (so the HTTP response
    is sent), then tells NSSM to restart the service. The backend process
    dies and NSSM starts a fresh one.
    """
    import threading

    def _do_restart():
        import subprocess
        import time

        time.sleep(1)
        try:
            subprocess.run(
                ["nssm", "restart", "tvtropes-mcp"],
                capture_output=True, timeout=30,
            )
        except Exception as exc:
            log.error("Restart failed: %s", exc)

    threading.Thread(target=_do_restart, daemon=True).start()
    _scraper.stop_crawler()
    return {"success": True, "message": "Restarting NSSM service..."}


@router.post("/scraper/start")
async def api_scraper_start() -> dict[str, Any]:
    return _scraper.start_crawler()


@router.post("/scraper/stop")
async def api_scraper_stop() -> dict[str, Any]:
    return _scraper.stop_crawler()


@router.get("/scraper/status")
async def api_scraper_status() -> dict[str, Any]:
    return _scraper.get_status()


@router.post("/scraper/pause")
async def api_scraper_pause() -> dict[str, Any]:
    return _scraper.pause_crawler()


@router.post("/scraper/resume")
async def api_scraper_resume() -> dict[str, Any]:
    return _scraper.resume_crawler()


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

    Rate-limited: max 1 crawl request every 30 seconds.
    Depth controls how many link-hops to follow (default 1 = only direct links).
    """
    import time as _time

    # Rate limit
    now = _time.time()
    if hasattr(api_scraper_crawl, "_last_call") and now - api_scraper_crawl._last_call < 30:
        wait = max(1, int(30 - (now - api_scraper_crawl._last_call)))
        return {"success": False, "error": f"Rate limited. Wait {wait}s before crawling again."}
    api_scraper_crawl._last_call = now

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
                            {"ns": e["namespace"], "name": e["page_name"]} for e in entries[: 10 - len(sample_links)]
                        )
                    added = await loop.run_in_executor(
                        None,
                        lambda e=entries: queue_urls(_db_path, e, priority=1),
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
    """Return current user settings (persisted in data/settings.json)."""
    from tvtropes_mcp.settings_manager import get_all

    return get_all()


@router.post("/settings")
async def api_settings_update(body: dict[str, Any]) -> dict[str, Any]:
    """Update user settings and persist to data/settings.json."""
    from tvtropes_mcp.settings_manager import update

    return update(body)


@router.post("/scraper/backup")
async def api_scraper_backup() -> dict[str, Any]:
    """Create a SQLite backup snapshot in data/backups/."""
    import sqlite3
    import time

    from scraper.db import get_conn

    backup_dir = _settings.resolved_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"tvtropes_{ts}.db"

    with get_conn(_db_path) as src:
        dst = sqlite3.connect(str(backup_path))
        src.backup(dst)
        dst.close()

    size_mb = round(backup_path.stat().st_size / (1024 * 1024), 2)
    log.info(f"Backup created: {backup_path} ({size_mb} MB)")

    existing = sorted(backup_dir.glob("*.db"), reverse=True)
    for old in existing[20:]:
        old.unlink()
        log.debug(f"Removed old backup: {old}")

    return {
        "success": True,
        "path": str(backup_path),
        "size_mb": size_mb,
        "backups_kept": min(len(existing), 20),
    }


@router.get("/ollama/status")
async def api_ollama_status() -> dict[str, Any]:
    """Check if Ollama / LM Studio is running and has the configured model."""
    import httpx

    from tvtropes_mcp.settings_manager import get_all as _get_sett

    s = _get_sett()
    api_mode = s.get("api_mode", "ollama")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            if api_mode == "openai":
                r = await client.get(f"{s['ollama_host']}/v1/models")
                if r.status_code == 200:
                    models = r.json().get("data", [])
                    model_names = [m["id"] for m in models]
                    chat_model = s.get("openai_chat_model", "")
                    configured_found = any(chat_model in m for m in model_names) if chat_model else True
                    return {
                        "running": True,
                        "host": s["ollama_host"],
                        "model_configured": chat_model,
                        "model_found": configured_found,
                        "models_available": model_names,
                    }
                return {"running": False, "host": s["ollama_host"], "error": f"HTTP {r.status_code}"}
            r = await client.get(f"{s['ollama_host']}/api/tags")
            if r.status_code == 200:
                models = r.json().get("models", [])
                model_names = [m["name"] for m in models]
                configured_found = any(m.startswith(s["ollama_model"]) for m in model_names)
                return {
                    "running": True,
                    "host": s["ollama_host"],
                    "model_configured": s["ollama_model"],
                    "model_found": configured_found,
                    "models_available": model_names,
                }
            return {"running": False, "host": s["ollama_host"], "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"running": False, "host": s["ollama_host"], "error": str(e)}


@router.post("/ollama/chat")
async def api_ollama_chat(body: dict[str, Any]) -> dict[str, Any]:
    """Simple LLM chat endpoint for the ChatPage AI assistant."""
    import httpx

    from tvtropes_mcp.settings_manager import get_all as _get_sett

    s = _get_sett()
    host = body.get("host", s["ollama_host"])
    model = body.get("model", s.get("openai_chat_model") if s.get("api_mode") == "openai" else s.get("ollama_model"))
    messages = body.get("messages", [])

    if not messages:
        return {"response": "No messages provided.", "error": True}

    try:
        async with httpx.AsyncClient(timeout=s.get("ollama_timeout", 120)) as client:
            if s.get("api_mode") == "openai":
                openai_msgs = []
                for m in messages:
                    role = "system" if m.get("role") == "system" else m.get("role", "user")
                    openai_msgs.append({"role": role, "content": m.get("content", "")})
                r = await client.post(
                    f"{host}/v1/chat/completions",
                    json={"model": model, "messages": openai_msgs, "temperature": 0.7},
                )
                if r.status_code == 200:
                    data = r.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {"response": content, "error": False}
                return {"response": f"LLM HTTP {r.status_code}", "error": True}
            r = await client.post(
                f"{host}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            if r.status_code == 200:
                data = r.json()
                return {"response": data.get("message", {}).get("content", ""), "error": False}
            return {"response": f"Ollama HTTP {r.status_code}", "error": True}
    except Exception as e:
        return {"response": f"LLM error: {e}", "error": True}


@router.post("/ollama/test")
async def api_ollama_test(body: dict[str, Any]) -> dict[str, Any]:
    """Test a specific LLM host+model combination."""
    import httpx

    host = body.get("host", "http://localhost:11434")
    model = body.get("model", "")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Try OpenAI-compatible /v1/models first, fallback to Ollama /api/tags
            r = await client.get(f"{host}/v1/models")
            if r.status_code == 200:
                models = r.json().get("data", [])
                model_names = [m["id"] for m in models] if models else []
                found = any(model in m for m in model_names) if model and model_names else True
                return {"success": True, "host": host, "reachable": True, "model_found": found, "models": model_names}
            r = await client.get(f"{host}/api/tags")
            if r.status_code == 200:
                models = r.json().get("models", [])
                model_names = [m["name"] for m in models]
                found = any(m.startswith(model) for m in model_names) if model else True
                return {"success": True, "host": host, "reachable": True, "model_found": found, "models": model_names}
            return {"success": False, "host": host, "reachable": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"success": False, "host": host, "reachable": False, "error": str(e)}


@router.get("/llm/discover")
async def api_llm_discover() -> dict[str, Any]:
    """Probe local LLM endpoints (Ollama, LM Studio) and return discovered models."""
    import httpx

    from tvtropes_mcp.settings_manager import get_all as _get_sett

    s = _get_sett()
    probes: list[tuple[str, str, str]] = [
        ("ollama", "Ollama", "http://localhost:11434/api/tags"),
        ("lmstudio", "LM Studio", "http://localhost:1234/v1/models"),
        ("vllm", "vLLM", "http://localhost:8000/v1/models"),
    ]
    providers: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=3.0) as client:
        for pid, label, url in probes:
            try:
                resp = await client.get(url)
                if resp.status_code < 500:
                    data = resp.json()
                    base_url = url.split("/api")[0].split("/v1")[0]
                    if pid == "ollama":
                        models = [m["name"] for m in data.get("models", [])]
                    else:
                        models = [m["id"] for m in data.get("data", [])]
                    providers.append({
                        "id": pid,
                        "label": label,
                        "base_url": base_url,
                        "models": models,
                        "online": True,
                    })
                else:
                    providers.append({
                        "id": pid, "label": label, "base_url": url.rsplit("/", 1)[0],
                        "models": [], "online": False,
                        "error": f"HTTP {resp.status_code}",
                    })
            except Exception as exc:
                providers.append({
                    "id": pid, "label": label, "base_url": "",
                    "models": [], "online": False,
                    "error": str(exc),
                })

    return {
        "providers": providers,
        "configured_host": s.get("ollama_host", "http://localhost:11434"),
        "configured_model": s.get("ollama_model", ""),
        "api_mode": s.get("api_mode", "ollama"),
        "configured_openai_model": s.get("openai_chat_model", ""),
    }


@router.get("/bridge")
async def api_bridge() -> dict[str, Any]:
    """Fleet bridge metadata — tells other MCP webapps how to deep-link here.

    Other servers (plex-mcp, calibre-mcp) use this to build one-click links.
    Follows the Cross-MCP Handoff Convention from WEBAPP_PORTS.md.
    """
    s = load_settings()
    return {
        "service": "tvtropes-mcp",
        "version": "0.2.0",
        "webapp_url": "http://127.0.0.1:10965",
        "deep_link_format": "http://127.0.0.1:10965/?lookup={namespace}/{page_name}",
        "api_lookup": f"http://{s.host}:{s.port}/api/lookup/title?title={{title}}&hint={{hint}}",
        "supported_hints": {
            "movie": "Film/ namespace",
            "show": "Series/ namespace",
            "anime": "Anime/ namespace",
            "book": "Literature/ namespace",
            "game": "VideoGame/ namespace",
        },
        "link_templates": {
            "plex_movie": "/?lookup=Film/{title}",
            "plex_show": "/?lookup=Series/{title}",
            "plex_anime": "/?lookup=Anime/{title}",
            "calibre_book": "/?lookup=Literature/{title}",
        },
    }


@router.get("/lookup/title")
async def api_lookup_title(
    title: str,
    hint: str | None = None,
) -> dict[str, Any]:
    """Resolve a title to a TVTropes page path.

    Used by other MCP webapps (Plex, Calibre) for cross-app deep-linking.
    The `hint` parameter narrows the search: 'movie', 'show', 'anime',
    'book', 'game', or a specific namespace like 'Film'.

    Returns the best-matching page in:
    {"found": bool, "namespace": str, "page_name": str,
     "url": str, "method": str}
    """
    from scraper.db import get_conn as _gconn

    # Map hints to namespace search order
    ns_map = {
        "movie": ["Film", "Main"],
        "show": ["Series", "Main"],
        "anime": ["Anime", "Main"],
        "book": ["Literature", "Main"],
        "game": ["VideoGame", "Main"],
        "comic": ["ComicBook", "Main"],
    }
    namespaces = ns_map.get(hint or "", [hint] if hint else None) or [
        "Film",
        "Series",
        "Anime",
        "Literature",
        "VideoGame",
        "Main",
        "Manga",
        "ComicBook",
        "VisualNovel",
        "Music",
        "WesternAnimation",
        "Webcomic",
        "WebOriginal",
        "Theatre",
    ]

    # Normalize title: strip spaces, handle common variations
    normalized = title.strip()
    candidates = [
        normalized,
        normalized.replace(" ", ""),
        normalized.replace(":", "").replace(" ", ""),
        normalized.replace("'", "").replace(" ", ""),
        normalized.replace("-", ""),
        normalized.replace("The ", "").replace("A ", "").replace("An ", ""),
    ]

    with _gconn(_db_path) as conn:
        for ns in namespaces:
            for cand in candidates:
                if not cand:
                    continue
                row = conn.execute(
                    "SELECT namespace, page_name, title FROM tropes WHERE namespace=? AND page_name LIKE ? LIMIT 1",
                    (ns, cand),
                ).fetchone()
                if row:
                    page_name = row["page_name"]
                    return {
                        "found": True,
                        "namespace": ns,
                        "page_name": page_name,
                        "title": row["title"],
                        "url": f"https://tvtropes.org/pmwiki/pmwiki.php/{ns}/{page_name}",
                        "webapp_url": f"/?lookup={ns}/{page_name}",
                        "method": "exact_match",
                    }

            # Fuzzy fallback: LIKE search within namespace
            like = f"%{cand.replace('%', '!%').replace('_', '!_')}%"
            row = conn.execute(
                "SELECT namespace, page_name, title FROM tropes "
                "WHERE namespace=? AND (page_name LIKE ? ESCAPE '!' "
                "OR title LIKE ? ESCAPE '!') LIMIT 1",
                (ns, like, like),
            ).fetchone()
            if row:
                return {
                    "found": True,
                    "namespace": row["namespace"],
                    "page_name": row["page_name"],
                    "title": row["title"],
                    "url": f"https://tvtropes.org/pmwiki/pmwiki.php/{row['namespace']}/{row['page_name']}",
                    "webapp_url": f"/?lookup={row['namespace']}/{row['page_name']}",
                    "method": "fuzzy_match",
                }

    return {"found": False, "title": title, "hint": hint}


@router.get("/log")
async def api_log(
    limit: int = 100,
    level: str | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Return recent log entries with optional level filter."""
    from tvtropes_mcp.log_ring import get_recent as _get_recent

    entries = _get_recent(limit=limit, level=level, offset=offset)
    return {
        "entries": entries,
        "total": len(entries),
        "filters": {"level": level, "limit": limit, "offset": offset},
    }


@router.get("/log/export")
async def api_log_export() -> dict[str, Any]:
    """Export all in-memory log entries as JSON."""
    from tvtropes_mcp.log_ring import export_json

    entries = export_json()
    return {"exported": len(entries), "entries": entries}


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
            f"SELECT COUNT(*) FROM pages WHERE {where}",
            params,
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
        row = conn.execute("SELECT url, content_hash FROM pages WHERE id=?", (page_id,)).fetchone()
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
        rows = conn.execute("SELECT namespace, page_name, title, description, laconic FROM tropes").fetchall()
    for row in rows:
        trope = dict(row)
        ok = await upsert_trope_embedding(
            _settings.resolved_data_dir(),
            trope,
            ollama_host=_settings.ollama_host,
            model=_settings.openai_embedding_model if _settings.api_mode == "openai" else "nomic-embed-text",
            api_mode=_settings.api_mode,
        )
        if ok:
            embedded += 1
        else:
            errors += 1
    return {"success": True, "embedded": embedded, "errors": errors, "total": embedded + errors}


@router.get("/skills")
async def api_skills() -> dict[str, Any]:
    """List available skills."""
    from pathlib import Path

    skills_dir = Path(__file__).resolve().parent / "skills"
    skills = []
    if skills_dir.is_dir():
        for child in skills_dir.iterdir():
            if child.is_dir() and (child / "SKILL.md").exists():
                skills.append({"name": child.name, "uri": f"skill://{child.name}/SKILL.md"})
    return {"skills": skills, "count": len(skills)}


@router.get("/skills/{skill_name}")
async def api_skill_content(skill_name: str) -> dict[str, Any]:
    """Return the raw SKILL.md content for a given skill."""
    from pathlib import Path

    skill_file = Path(__file__).resolve().parent / "skills" / skill_name / "SKILL.md"
    if skill_file.exists():
        return {"name": skill_name, "content": skill_file.read_text(encoding="utf-8")}
    return {"name": skill_name, "content": "", "error": "Skill not found"}


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
            "web_search",
        ],
        "mcp_http_path": "/mcp",
        "prompts": [
            "trope_analysis_prompt",
            "creative_writing_prompt",
            "recommendation_prompt",
            "trope_deep_dive_prompt",
            "calibre_integration_prompt",
        ],
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

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": "tvtropes-mcp"}

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
