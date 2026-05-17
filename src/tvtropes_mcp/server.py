"""FastMCP 3.2 server: TVTropes query interface against local SQLite mirror."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

from tvtropes_mcp.config import load_settings
from tvtropes_mcp.db import (
    ensure_db,
    random_trope_get,
)
from tvtropes_mcp.db import (
    namespace_list as db_namespace_list,
)
from tvtropes_mcp.db import (
    related_tropes as db_related_tropes,
)
from tvtropes_mcp.db import (
    scraper_status as db_scraper_status,
)
from tvtropes_mcp.db import (
    trope_examples as db_trope_examples,
)
from tvtropes_mcp.db import (
    trope_get as db_trope_get,
)
from tvtropes_mcp.db import (
    trope_search as db_trope_search,
)
from tvtropes_mcp.db import (
    work_tropes as db_work_tropes,
)
from tvtropes_mcp.scraper_manager import ScraperManager

log = logging.getLogger(__name__)

_settings = load_settings()
_db_path = str(_settings.resolved_data_dir() / "tvtropes.db")
ensure_db(_db_path)

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

_scraper_manager: ScraperManager | None = None


def _get_manager() -> ScraperManager:
    global _scraper_manager
    if _scraper_manager is None:
        _scraper_manager = ScraperManager(_db_path)
    return _scraper_manager


@mcp.tool(annotations={"readOnlyHint": True})
async def trope_search(
    query: str,
    limit: int = 20,
    ctx: Context = None,
) -> dict[str, Any]:
    """Full-text search over trope names and descriptions using SQLite FTS5.

    ## Return Format
    {"success": bool, "query": str, "total": int,
     "results": [{"id": str, "name": str, "snippet": str,
                  "score": float, "namespace": str}]}

    ## Examples
    trope_search("villain redemption")
    trope_search("time loop", limit=5)
    """
    try:
        results = db_trope_search(query, limit=limit, db_path=_db_path)
        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results),
        }
    except Exception as e:
        log.error(f"trope_search failed: {e}", exc_info=True)
        return {"success": False, "query": query, "results": [], "total": 0, "error": str(e)}


@mcp.tool(annotations={"readOnlyHint": True})
async def trope_get(
    trope_id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a full trope page — description, examples, and related tropes.

    ## Return Format
    {"success": bool,
     "trope": {"id": str, "name": str, "description": str,
               "examples": list, "sub_tropes": list,
               "super_tropes": list, "sister_tropes": list,
               "related_tropes": list}}

    ## Examples
    trope_get("Main/ChekhovsGun")
    """
    try:
        result = db_trope_get(trope_id, db_path=_db_path)
        if result is None:
            return {"success": False, "trope": None, "error": f"Trope not found: {trope_id}"}
        return {"success": True, "trope": result}
    except Exception as e:
        log.error(f"trope_get failed: {e}", exc_info=True)
        return {"success": False, "trope": None, "error": str(e)}


@mcp.tool(annotations={"readOnlyHint": True})
async def work_tropes(
    work_id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all tropes for a given work.

    ## Return Format
    {"success": bool, "work": {"id": str}, "count": int,
     "tropes": [{"trope_ns": str, "trope_name": str,
                 "title": str, "description": str}]}

    ## Examples
    work_tropes("Series/BreakingBad")
    """
    try:
        results = db_work_tropes(work_id, db_path=_db_path)
        return {
            "success": True,
            "work": {"id": work_id},
            "tropes": results,
            "count": len(results),
        }
    except Exception as e:
        log.error(f"work_tropes failed: {e}", exc_info=True)
        return {"success": False, "work": {"id": work_id}, "tropes": [], "count": 0, "error": str(e)}


@mcp.tool(annotations={"readOnlyHint": True})
async def trope_examples(
    trope_id: str,
    namespace: str | None = None,
    limit: int = 20,
    ctx: Context = None,
) -> dict[str, Any]:
    """Get examples of a trope, optionally filtered by namespace/medium.

    ## Return Format
    {"success": bool, "trope": str, "examples": [{"work_ns": str, "work_name": str, "example_text": str}], "count": int}

    ## Examples
    trope_examples("Main/FiveManBand", namespace="Film")
    trope_examples("Main/TheChosenOne", limit=5)
    """
    try:
        results = db_trope_examples(trope_id, namespace=namespace, limit=limit, db_path=_db_path)
        return {
            "success": True,
            "trope": trope_id,
            "examples": results,
            "count": len(results),
        }
    except Exception as e:
        log.error(f"trope_examples failed: {e}", exc_info=True)
        return {"success": False, "trope": trope_id, "examples": [], "count": 0, "error": str(e)}


@mcp.tool(annotations={"readOnlyHint": True})
async def related_tropes(
    trope_id: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Traverse trope relationships — SubTrope, SuperTrope, SisterTrope, Related.

    ## Return Format
    {"success": bool, "trope": str,
     "sub_tropes": list, "super_tropes": list,
     "sister_tropes": list, "related_tropes": list}

    ## Examples
    related_tropes("Main/AntiHero")
    """
    try:
        result = db_related_tropes(trope_id, db_path=_db_path)
        return {
            "success": True,
            "trope": trope_id,
            **result,
        }
    except Exception as e:
        log.error(f"related_tropes failed: {e}", exc_info=True)
        return {
            "success": False,
            "trope": trope_id,
            "sub_tropes": [],
            "super_tropes": [],
            "sister_tropes": [],
            "related_tropes": [],
            "error": str(e),
        }


@mcp.tool(annotations={"readOnlyHint": True})
async def namespace_list(
    ctx: Context = None,
) -> dict[str, Any]:
    """List all namespaces and their page counts from the mirror database.

    ## Return Format
    {"success": bool, "namespaces": [{"namespace": str, "page_count": int}]}

    ## Examples
    namespace_list()
    """
    try:
        namespaces = db_namespace_list(db_path=_db_path)
        return {"success": True, "namespaces": namespaces}
    except Exception as e:
        log.error(f"namespace_list failed: {e}", exc_info=True)
        return {"success": False, "namespaces": [], "error": str(e)}


@mcp.tool(annotations={"readOnlyHint": True})
async def random_trope(
    ctx: Context = None,
) -> dict[str, Any]:
    """Get a random trope from the mirror database.

    ## Return Format
    {"success": bool,
     "trope": {"id": str, "name": str, "description": str,
               "example_count": int, "namespace": str,
               "page_name": str}}

    ## Examples
    random_trope()
    """
    try:
        result = random_trope_get(db_path=_db_path)
        if result is None:
            return {"success": False, "trope": None, "message": "No tropes in database yet — run the scraper first"}
        return {"success": True, "trope": result}
    except Exception as e:
        log.error(f"random_trope failed: {e}", exc_info=True)
        return {"success": False, "trope": None, "error": str(e)}


@mcp.tool(annotations={"readOnlyHint": True})
async def scraper_status(
    ctx: Context = None,
) -> dict[str, Any]:
    """Get scraper progress: crawl stats, DB size, extraction backlog.

    ## Return Format
    {"success": bool,
     "crawl": {"pages_visited": int, "pages_queued": int,
               "pages_total_estimate": int, "pages_failed": int,
               "daily": int},
     "db": {"size_mb": float, "tropes": int, "examples": int,
            "trope_relations": int, "work_tropes": int},
     "ollama": {"queue_depth": int, "avg_latency_ms": float}}

    ## Examples
    scraper_status()
    """
    try:
        manager = _get_manager()
        status = manager.get_status()
        stats = db_scraper_status(db_path=_db_path)
        stats["crawler"] = {
            "running": status.get("crawler", {}).get("running", False),
            "session_id": status.get("crawler", {}).get("session_id"),
        }
        return {"success": True, **stats}
    except Exception as e:
        log.error(f"scraper_status failed: {e}", exc_info=True)
        return {
            "success": False,
            "crawl": {"pages_visited": 0, "pages_queued": 0, "pages_total_estimate": 220000},
            "db": {"size_mb": 0.0, "tropes": 0, "examples": 0, "trope_relations": 0, "work_tropes": 0},
            "ollama": {"queue_depth": 0, "avg_latency_ms": 0.0},
            "error": str(e),
        }
