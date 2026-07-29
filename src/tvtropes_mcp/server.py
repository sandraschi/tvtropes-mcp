"""FastMCP 3.2 server: TVTropes query interface against local SQLite mirror."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastmcp import Context, FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider
from fastmcp.server.server import ToolResult
from prefab_ui import PrefabApp
from prefab_ui.components import Heading, Row
from pydantic import Field

from tvtropes_mcp.config import load_settings
from tvtropes_mcp.db import ensure_db, random_trope_get
from tvtropes_mcp.db import namespace_list as db_namespace_list
from tvtropes_mcp.db import related_tropes as db_related_tropes
from tvtropes_mcp.db import scraper_status as db_scraper_status
from tvtropes_mcp.db import trope_examples as db_trope_examples
from tvtropes_mcp.db import trope_get as db_trope_get
from tvtropes_mcp.db import trope_search as db_trope_search
from tvtropes_mcp.db import work_tropes as db_work_tropes
from tvtropes_mcp.db import works_in_namespace as db_works_in_namespace
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


@mcp.tool(annotations={"readOnlyHint": True}, version="1.0.0", output_schema={"type": "object"})
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
async def works_in_namespace(
    namespace: Annotated[str, Field(description="Namespace to list works in (e.g. 'Film', 'Series', 'Anime').")],
    limit: Annotated[int, Field(description="Max results.", ge=1, le=200)] = 50,
    offset: Annotated[int, Field(description="Offset for pagination.", ge=0)] = 0,
    ctx: Context = None,
) -> dict[str, Any]:
    """List works in a given namespace for browsing.

    Returns works that have been extracted from the mirror, ordered by name.
    Use this to discover works to drill into with work_tropes.

    ## Return Format
    {"success": bool, "namespace": str, "works": [{"work_name": str, "namespace": str}], "total": int}

    ## Examples
    works_in_namespace(namespace="Film", limit=20)
    works_in_namespace(namespace="Anime", offset=40)
    """
    try:
        works = db_works_in_namespace(namespace, db_path=_db_path, limit=limit, offset=offset)
        return {"success": True, "namespace": namespace, "works": works, "total": len(works)}
    except Exception as e:
        log.error(f"works_in_namespace failed: {e}", exc_info=True)
        return {"success": False, "namespace": namespace, "works": [], "total": 0, "error": str(e)}


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
            model=_settings.openai_embedding_model if _settings.api_mode == "openai" else "nomic-embed-text",
            api_mode=_settings.api_mode,
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


@mcp.tool(annotations={"readOnlyHint": True})
async def web_search(
    query: Annotated[str, Field(description="Search query for the web.")],
    engine: Annotated[str, Field(description="Search engine to use.")] = "google",
    limit: Annotated[int, Field(description="Max results.", ge=1, le=20)] = 5,
    ctx: Context = None,
) -> dict[str, Any]:
    """Search the web via the local OpenSERP server for trope context not in the mirror yet.

    Requires a running OpenSERP instance on localhost:7000
    (`npx -y @openserp/mcp` or the standalone binary).
    Engines: google, bing, duckduckgo, yandex, baidu, ecosia.

    ## Return Format
    {"success": bool, "query": str, "engine": str,
     "results": [{"title": str, "url": str, "snippet": str}], "total": int}

    ## Examples
    web_search("Chekhov's Gun examples in modern film")
    web_search("trope: Batman as Byronic hero", engine="duckduckgo")
    """
    base = _settings.openserp_url
    url = f"{base}/{engine}/search"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params={"text": query, "limit": limit})
            r.raise_for_status()
            data = r.json()
    except httpx.ConnectError:
        return {
            "success": False,
            "query": query,
            "engine": engine,
            "results": [],
            "total": 0,
            "error": "OpenSERP not reachable — start it with `npx -y @openserp/mcp` or `openserp serve`",
        }
    except Exception as e:
        log.error(f"web_search failed: {e}", exc_info=True)
        return {"success": False, "query": query, "engine": engine, "results": [], "total": 0, "error": str(e)}

    results = []
    for r_item in data.get("results", []):
        results.append(
            {
                "title": r_item.get("title", ""),
                "url": r_item.get("url", ""),
                "snippet": r_item.get("snippet", ""),
            }
        )
    return {
        "success": True,
        "query": query,
        "engine": engine,
        "results": results,
        "total": len(results),
    }


@mcp.tool(app=True, annotations={"readOnlyHint": True})
async def show_status_card(ctx: Context = None) -> ToolResult:
    """Display scraper and database status as a rich in-chat Prefab card.

    ## Return Format
    ToolResult with plain text fallback + PrefabApp structured content.
    """
    from tvtropes_mcp.db import scraper_status as db_scraper_status
    from tvtropes_mcp.server import mcp

    db_stats = db_scraper_status(db_path=_db_path)
    tools = await mcp.list_tools()
    app = PrefabApp(title="tvtropes-mcp Status")
    with app:
        Heading("Database")
        Row(label="Tropes", value=str(db_stats.get("tropes", 0)))
        Row(label="Examples", value=str(db_stats.get("examples", 0)))
        Row(label="Relations", value=str(db_stats.get("trope_relations", 0)))
        Row(label="DB Size", value=f"{db_stats.get('size_mb', 0):.1f} MB")
        Heading("Crawl")
        Row(label="Crawled", value=str(db_stats.get("crawled", 0)))
        Row(label="Pending", value=str(db_stats.get("pending", 0)))
        Row(label="Extracted", value=str(db_stats.get("extracted", 0)))
        Row(label="Failed", value=str(db_stats.get("failed", 0)))
        Row(label="Daily", value=str(db_stats.get("daily", 0)))
        Heading("Server")
        Row(label="Tools", value=str(len(tools) if tools else 13))
        Row(label="Backend", value="10964")
    return ToolResult(
        content=f"tvtropes-mcp: {db_stats.get('tropes', 0)} tropes, "
        f"{db_stats.get('trope_relations', 0)} relations, "
        f"{db_stats.get('crawled', 0)} pages crawled",
        structured_content=app,
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def trope_agentic_assist(
    goal: str,
    ctx: Context = None,
) -> dict:
    """Multi-step research plan via MCP sampling (FastMCP 3.1+).

    When the host exposes sampling (Claude Desktop), this tool uses
    ``ctx.sample()`` to autonomously search, browse, and traverse the
    trope graph to answer complex questions. Falls back to a structured
    plan when sampling is not available.

    ## Return Format
    {"success": bool, "result": str, "mode": str}

    ## Examples
    trope_agentic_assist("Compare the tropes in Breaking Bad and The Wire")
    trope_agentic_assist("Find works that subvert the Chosen One trope")
    """
    system = (
        "You are a TVTropes expert. You have these tools available:\n"
        "- trope_search(query, limit) — full-text search across tropes\n"
        "- trope_get(trope_id) — full trope page with relations\n"
        "- work_tropes(work_id) — all tropes for a work\n"
        "- related_tropes(trope_id) — traverse the trope graph\n"
        "- semantic_search(query, limit) — vector similarity search\n"
        "- web_search(query) — web search for external context\n\n"
        f"Goal: {goal}\n\n"
        "Use the tools step by step to research. Present your findings concisely."
    )
    if ctx and hasattr(ctx, "sample") and callable(ctx.sample):
        try:
            result = await ctx.sample(system)
            return {"success": True, "result": str(result), "mode": "sampling"}
        except Exception as exc:
            return {
                "success": False,
                "result": "",
                "mode": "error",
                "error": f"Sampling failed: {exc}",
            }
    return {
        "success": True,
        "result": "MCP sampling is not available on this host. "
        f"To research '{goal}', call these tools manually:\n"
        "1. trope_search for broad keyword discovery\n"
        "2. trope_get / work_tropes for details\n"
        "3. related_tropes for graph traversal",
        "mode": "plan",
    }


# ─── Prompts ────────────────────────────────────────────────────────


@mcp.prompt
async def trope_analysis_prompt(work_id: str) -> str:
    """Analyse the tropes used in a specific work (film, series, anime, etc.).

    ## Return Format
    A structured prompt string for the AI to analyse tropes in a work.

    ## Examples
    get_prompt("trope_analysis_prompt", {"work_id": "Series/BreakingBad"})
    """
    return (
        f"You are analysing the work {work_id} from the TVTropes mirror. "
        f"Use the work_tropes tool to look up all tropes associated with {work_id}. "
        f"For each trope returned, use trope_get to retrieve its full description, "
        f"examples, and relationships. Then:\n\n"
        f"1. Identify the 5-10 most defining tropes for this work\n"
        f"2. Explain how each trope functions in the narrative\n"
        f"3. Note any subversions or unusual uses of tropes\n"
        f"4. Identify the work's primary genre through its trope cluster\n"
        f"5. Suggest similar works based on trope overlap\n\n"
        f"Present your analysis as a structured report with sections."
    )


@mcp.prompt
async def creative_writing_prompt(genre: str = "fantasy", tone: str = "dark") -> str:
    """Generate story ideas by combining tropes from the TVTropes mirror.

    ## Return Format
    A structured prompt string for AI-assisted creative writing.

    ## Examples
    get_prompt("creative_writing_prompt", {"genre": "sci-fi", "tone": "hopeful"})
    """
    return (
        f"You are helping develop a {tone} {genre} story. "
        f"Use the random_trope tool to discover unexpected tropes, "
        f"and related_tropes to build a trope constellation. Then:\n\n"
        f"1. Pick 3 tropes that could form the core of a {tone} {genre} narrative\n"
        f"2. For each trope, use trope_get to read its description and examples\n"
        f"3. Propose a story premise that combines all 3 tropes\n"
        f"4. Suggest character archetypes that fit these tropes\n"
        f"5. Outline a 3-act structure showing where each trope appears\n\n"
        f"Be creative — the best stories come from unexpected trope combinations."
    )


@mcp.prompt
async def recommendation_prompt(work_id: str, limit: int = 5) -> str:
    """Find similar works based on shared tropes.

    ## Return Format
    A structured prompt string for AI-powered recommendations.

    ## Examples
    get_prompt("recommendation_prompt", {"work_id": "Anime/NeonGenesisEvangelion", "limit": 5})
    """
    return (
        f"Recommend works similar to {work_id} using the TVTropes mirror. "
        f"Use work_tropes to get the trope profile of {work_id}, "
        f"then search for other works that share the most distinctive tropes. "
        f"Focus on tropes that are specific to this work's genre and style, "
        f"rather than universal tropes. For each recommendation:\n\n"
        f"1. Name the work and its namespace\n"
        f"2. List the shared tropes\n"
        f"3. Explain why a fan of {work_id} would enjoy it\n"
        f"4. Note any tropes that are unique to this recommendation\n\n"
        f"Return up to {limit} recommendations ranked by relevance."
    )


@mcp.prompt
async def trope_deep_dive_prompt(trope_id: str) -> str:
    """Deep-dive into a single trope: history, variations, and notable examples.

    ## Return Format
    A structured prompt string for AI-assisted trope research.

    ## Examples
    get_prompt("trope_deep_dive_prompt", {"trope_id": "Main/ChekhovsGun"})
    """
    return (
        f"Research the trope {trope_id} thoroughly using the TVTropes mirror. "
        f"Use trope_get to retrieve the full page, then related_tropes to "
        f"explore its position in the trope graph. Structure your report:\n\n"
        f"1. **Definition**: What is this trope? Include the laconic summary.\n"
        f"2. **History**: When did this trope get named? Any notable origins?\n"
        f"3. **Relationships**: What are its sub-tropes, super-tropes, and sister tropes?\n"
        f"4. **Notable examples**: Pick 3-5 of the best examples from different media\n"
        f"5. **Variations**: How has this trope evolved or been subverted?\n"
        f"6. **Writing advice**: How can a writer use this trope effectively?\n\n"
        f"For each relationship link, use related_tropes to follow the chain "
        f"one level deeper."
    )


@mcp.prompt
async def calibre_integration_prompt(title: str) -> str:
    """Cross-reference a Calibre book against the TVTropes Literature/ namespace.

    ## Return Format
    A structured prompt string for AI-assisted book trope analysis.

    ## Examples
    get_prompt("calibre_integration_prompt", {"title": "Harry Potter"})
    """
    return (
        f"A book titled '{title}' was found in your Calibre library. "
        f"Use trope_lookup_by_title to search the TVTropes mirror for this title "
        f"in the Literature/ namespace. If found, use work_tropes to get its "
        f"trope profile, then trope_get on the most interesting tropes. "
        f"Finally:\n\n"
        f"1. List the key tropes associated with this book\n"
        f"2. Recommend 2-3 other books with similar trope profiles\n"
        f"3. Identify the genre cluster this book belongs to\n\n"
        f"If the book is not found in the mirror, suggest possible page names "
        f"to check, or note that it may not yet have been crawled."
    )
