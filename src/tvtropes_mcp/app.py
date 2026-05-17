"""FastAPI: REST dashboard API + mounted FastMCP HTTP (streamable)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI

from tvtropes_mcp.config import load_settings
from tvtropes_mcp.server import mcp

mcp_http = mcp.http_app(path="/mcp")
router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "tvtropes-mcp"}


@router.get("/status")
async def api_status() -> dict[str, Any]:
    return {
        "scraper": {"state": "not_started", "pages_visited": 0, "pages_queued": 0},
        "db": {"size_mb": 0.0, "tropes": 0, "examples": 0},
        "ollama": {"queue_depth": 0, "avg_latency_ms": 0.0},
    }


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
        ],
        "mcp_http_path": "/mcp",
    }


def build_app() -> FastAPI:
    settings = load_settings()
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="tvtropes-mcp",
        version="0.1.0",
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
            "version": "0.1.0",
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
            "version": "0.1.0",
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
