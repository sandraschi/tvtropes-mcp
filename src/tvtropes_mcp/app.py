"""FastAPI: REST dashboard API + mounted FastMCP HTTP (streamable)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI

from tvtropes_mcp.config import load_settings
from tvtropes_mcp.db import (
    ensure_db,
)
from tvtropes_mcp.db import (
    scraper_status as db_scraper_status,
)
from tvtropes_mcp.scraper_manager import ScraperManager
from tvtropes_mcp.server import mcp

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
