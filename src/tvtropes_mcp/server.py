"""FastMCP 3.2 server: TVTropes query interface against local SQLite mirror."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

from fastmcp import Context, FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider
from pydantic import Field

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


@mcp.tool(annotations={"readOnlyHint": True}, version="1.0.0")
async def trope_search(
    query: Annotated[str, Field(description="Full-text query for trope names and descriptions (FTS5).")],
    limit: Annotated[int, Field(description="Max results.", ge=1, le=100)] = 20,
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


@mcp.tool(annotations={"readOnlyHint": True})
async def trope_lookup_by_title(
    title: str,
    ctx: Context = None,
) -> dict[str, Any]:
    """Cross-reference a book title against the Literature/ trope index.

    Searches the trope mirror for works matching the given title in the
    Literature namespace, and also runs an FTS search on title keywords.

    ## Return Format
    {"success": bool, "book_title": str, "direct_literature_match": list,
     "fts_results": list, "total_direct": int, "total_fts": int}

    ## Examples
    trope_lookup_by_title("Harry Potter")
    """
    try:
        from tvtropes_mcp.calibre_ops import lookup_tropes_for_book

        return lookup_tropes_for_book(title, db_path=_db_path)
    except Exception as e:
        log.error(f"trope_lookup_by_title failed: {e}", exc_info=True)
        return {
            "success": False,
            "book_title": title,
            "direct_literature_match": [],
            "fts_results": [],
            "total_direct": 0,
            "total_fts": 0,
            "error": str(e),
        }


@mcp.tool(annotations={"readOnlyHint": True})
async def calibre_search(
    title: str | None = None,
    author: str | None = None,
    limit: int = 10,
    ctx: Context = None,
) -> dict[str, Any]:
    """Search the local Calibre library for books by title or author.

    ## Return Format
    {"success": bool, "query": dict, "books": list, "total": int}

    ## Examples
    calibre_search(title="Harry Potter")
    calibre_search(author="Sanderson")
    """
    try:
        from tvtropes_mcp.calibre_ops import find_calibre_db, search_books

        calibre_db = find_calibre_db()
        if calibre_db is None:
            return {
                "success": False,
                "query": {"title": title, "author": author},
                "books": [],
                "total": 0,
                "error": "Calibre library not found",
            }
        books = search_books(title=title, author=author, limit=limit, calibre_db=calibre_db)
        return {
            "success": True,
            "query": {"title": title, "author": author},
            "books": books,
            "total": len(books),
        }
    except Exception as e:
        log.error(f"calibre_search failed: {e}", exc_info=True)
        return {"success": False, "query": {"title": title, "author": author}, "books": [], "total": 0, "error": str(e)}


@mcp.tool(annotations={"readOnlyHint": True})
async def calibre_status(
    ctx: Context = None,
) -> dict[str, Any]:
    """Check if a Calibre library is available on this machine.

    ## Return Format
    {"success": bool, "found": bool, "library_path": str|None, "book_count": int}

    ## Examples
    calibre_status()
    """
    try:
        from tvtropes_mcp.calibre_ops import calibre_status as _calibre_status
        result = _calibre_status()
        return {"success": True, **result}
    except Exception as e:
        log.error(f"calibre_status failed: {e}", exc_info=True)
        return {"success": False, "found": False, "library_path": None, "book_count": 0, "error": str(e)}


@mcp.tool(annotations={"readOnlyHint": True})
async def semantic_search(
    query: Annotated[str, Field(description="Natural language query to search semantically.")],
    limit: Annotated[int, Field(description="Max results.", ge=1, le=50)] = 10,
    ctx: Context = None,
) -> dict[str, Any]:
    """Semantic (vector) search over tropes using LanceDB + Ollama embeddings.

    Requires Ollama with nomic-embed-text running. Returns tropes ranked by
    semantic similarity to the query, not keyword match.

    ## Return Format
    {"success": bool, "query": str, "total": int,
     "results": [{"id": str, "title": str,
                  "description": str, "score": float}]}

    ## Examples
    semantic_search("stories about redemption and sacrifice")
    semantic_search("time paradoxes in fiction", limit=5)
    """
    from tvtropes_mcp.vector_store import semantic_search as _semantic_search

    try:
        results = await _semantic_search(
            query,
            _settings.resolved_data_dir(),
            limit=limit,
            ollama_host=_settings.ollama_host,
        )
        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results),
        }
    except Exception as e:
        log.error(f"semantic_search failed: {e}", exc_info=True)
        return {"success": False, "query": query, "results": [], "total": 0, "error": str(e)}
