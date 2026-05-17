"""FastMCP 3.2 server: TVTropes query interface (stubs — implementation deferred)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

log = logging.getLogger(__name__)

mcp = FastMCP(
    "tvtropes-mcp",
    instructions=(
        "TVTropes knowledge graph: search tropes, browse works, traverse trope relationships. "
        "Data is sourced from a local SQLite mirror populated by the background scraper. "
        "All tools are read-only queries against the mirror database."
    ),
)

_skills_dir = Path(__file__).resolve().parent / "skills"
if _skills_dir.is_dir():
    mcp.add_provider(SkillsDirectoryProvider(roots=[_skills_dir]))


@mcp.tool(annotations={"readOnlyHint": True})
async def trope_search(
    query: str,
    limit: int = 20,
    ctx: Context = None,
) -> dict[str, Any]:
    """Full-text search over trope names and descriptions.

    ## Return Format
    {"success": bool, "results": [{"id": str, "name": str, "snippet": str, "score": float}], "total": int}

    ## Examples
    trope_search("villain redemption")
    trope_search("time loop", limit=5)
    """
    return {"success": False, "results": [], "total": 0, "message": "Implementation deferred — see docs/SCRAPER_PLAN.md"}


@mcp.tool(annotations={"readOnlyHint": True})
async def trope_get(
    trope_id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a full trope page — description, examples, related tropes.

    ## Return Format
    {"success": bool, "trope": {"id": str, "name": str, "description": str, "examples": list, "related": list}}

    ## Examples
    trope_get("Main/ChekhovsGun")
    """
    return {"success": False, "trope": None, "message": "Implementation deferred — see docs/SCRAPER_PLAN.md"}


@mcp.tool(annotations={"readOnlyHint": True})
async def work_tropes(
    work_id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all tropes for a given work.

    ## Return Format
    {"success": bool, "work": {"id": str, "title": str}, "tropes": [{"id": str, "name": str}], "count": int}

    ## Examples
    work_tropes("Series/BreakingBad")
    """
    return {"success": False, "work": None, "tropes": [], "count": 0, "message": "Implementation deferred — see docs/SCRAPER_PLAN.md"}


@mcp.tool(annotations={"readOnlyHint": True})
async def trope_examples(
    trope_id: str,
    namespace: str | None = None,
    limit: int = 20,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get examples of a trope, optionally filtered by namespace/medium.

    ## Return Format
    {"success": bool, "trope": str, "examples": [{"work": str, "text": str, "namespace": str}], "count": int}

    ## Examples
    trope_examples("Main/FiveManBand", namespace="Film")
    trope_examples("Main/TheChosenOne", limit=5)
    """
    return {"success": False, "trope": trope_id, "examples": [], "count": 0, "message": "Implementation deferred — see docs/SCRAPER_PLAN.md"}


@mcp.tool(annotations={"readOnlyHint": True})
async def related_tropes(
    trope_id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Traverse trope relationships — SubTrope, SuperTrope, SisterTrope.

    ## Return Format
    {"success": bool, "trope": str, "sub_tropes": list, "super_tropes": list, "sister_tropes": list}

    ## Examples
    related_tropes("Main/AntiHero")
    """
    return {"success": False, "trope": trope_id, "sub_tropes": [], "super_tropes": [], "sister_tropes": [], "message": "Implementation deferred — see docs/SCRAPER_PLAN.md"}


@mcp.tool(annotations={"readOnlyHint": True})
async def namespace_list(
    ctx: Context = None,
) -> dict[str, Any]:
    """List all namespaces and their page counts.

    ## Return Format
    {"success": bool, "namespaces": [{"name": str, "page_count": int}]}

    ## Examples
    namespace_list()
    """
    return {"success": False, "namespaces": [], "message": "Implementation deferred — see docs/SCRAPER_PLAN.md"}


@mcp.tool(annotations={"readOnlyHint": True})
async def random_trope(
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a random trope, weighted by example count.

    ## Return Format
    {"success": bool, "trope": {"id": str, "name": str, "description": str, "example_count": int}}

    ## Examples
    random_trope()
    """
    return {"success": False, "trope": None, "message": "Implementation deferred — see docs/SCRAPER_PLAN.md"}


@mcp.tool(annotations={"readOnlyHint": True})
async def scraper_status(
    ctx: Context = None,
) -> dict[str, Any]:
    """Get scraper progress: crawl stats, queue depth, Ollama backlog, DB size.

    ## Return Format
    {"success": bool, "crawl": {"pages_visited": int, "pages_queued": int, "pages_total_estimate": int}, "db": {"size_mb": float, "tropes": int, "examples": int}, "ollama": {"queue_depth": int, "avg_latency_ms": float}}

    ## Examples
    scraper_status()
    """
    return {
        "success": True,
        "crawl": {"pages_visited": 0, "pages_queued": 0, "pages_total_estimate": 220000},
        "db": {"size_mb": 0.0, "tropes": 0, "examples": 0},
        "ollama": {"queue_depth": 0, "avg_latency_ms": 0.0},
        "message": "Scraper not yet implemented — see docs/SCRAPER_PLAN.md",
    }
