"""Read-only query layer for MCP tools — re-exports from scraper.db with MCP-friendly formatting."""

from __future__ import annotations

from typing import Any

from scraper.db import (
    get_crawl_stats,
    get_db_stats,
    get_related_tropes,
    get_trope,
    get_trope_examples,
    get_work_tropes,
    init_db,
    list_namespaces,
    random_trope,
    search_tropes,
)

_QUERY_LIMIT = 1000


def ensure_db(db_path: str) -> None:
    init_db(db_path)


def trope_search(query: str, limit: int = 20, db_path: str | None = None) -> list[dict[str, Any]]:
    results = search_tropes(db_path, query, limit=min(limit, _QUERY_LIMIT))
    return [
        {
            "id": f"{r['namespace']}/{r['page_name'] if r['page_name'] else ''}",
            "name": r.get("title") or r.get("page_name") or "Unknown",
            "snippet": (r.get("description") or "")[:200],
            "score": round(float(r.get("rank", 0)), 4),
            "namespace": r.get("namespace"),
            "page_name": r.get("page_name"),
        }
        for r in results
    ]


def trope_get(trope_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    result = get_trope(db_path, trope_id)
    if result is None:
        return None
    return {
        "id": f"{result['namespace']}/{result['page_name']}",
        "name": result.get("title") or result.get("page_name") or "Unknown",
        "title": result.get("title"),
        "description": result.get("description"),
        "laconic": result.get("laconic"),
        "image_url": result.get("image_url"),
        "examples": [
            {
                "work": f"{e['work_ns']}/{e['work_name']}" if e.get("work_name") else None,
                "namespace": e.get("work_ns"),
                "work_name": e.get("work_name"),
                "text": e.get("example_text"),
            }
            for e in (result.get("examples") or [])
        ],
        "sub_tropes": result.get("sub_tropes", []),
        "super_tropes": result.get("super_tropes", []),
        "sister_tropes": result.get("sister_tropes", []),
        "related_tropes": result.get("related_tropes", []),
    }


def work_tropes(work_id: str, db_path: str | None = None) -> list[dict[str, Any]]:
    return get_work_tropes(db_path, work_id)


def trope_examples(
    trope_id: str,
    namespace: str | None = None,
    limit: int = 20,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    return get_trope_examples(db_path, trope_id, namespace=namespace, limit=min(limit, _QUERY_LIMIT))


def related_tropes(trope_id: str, db_path: str | None = None) -> dict[str, list[dict[str, str]]]:
    return get_related_tropes(db_path, trope_id)


def namespace_list(db_path: str | None = None) -> list[dict[str, Any]]:
    return list_namespaces(db_path)


def works_in_namespace(
    namespace: str,
    db_path: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    from scraper.db import get_conn as _gconn

    with _gconn(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT work_name FROM work_tropes WHERE work_ns=? ORDER BY work_name LIMIT ? OFFSET ?",
            (namespace, limit, offset),
        ).fetchall()
        return [{"work_name": r["work_name"], "namespace": namespace} for r in rows]


def random_trope_get(db_path: str | None = None) -> dict[str, Any] | None:
    result = random_trope(db_path)
    if result is None:
        return None
    return {
        "id": f"{result['namespace']}/{result['page_name']}",
        "name": result.get("title") or result.get("page_name") or "Unknown",
        "description": result.get("description"),
        "example_count": result.get("example_count", 0),
        "namespace": result.get("namespace"),
        "page_name": result.get("page_name"),
    }


def scraper_status(db_path: str | None = None) -> dict[str, Any]:
    crawl = get_crawl_stats(db_path)
    db_stats = get_db_stats(db_path)
    return {
        "crawl": {
            "pages_visited": crawl.get("extracted", 0) + crawl.get("crawled", 0),
            "pages_queued": crawl.get("pending", 0),
            "pages_total_estimate": 220000,
            "pages_crawling": crawl.get("crawling", 0),
            "pages_failed": crawl.get("failed", 0),
            "pages_skipped": crawl.get("skipped", 0),
            "pages_blocked": crawl.get("blocked", 0),
            "daily": crawl.get("daily", 0),
        },
        "db": {
            "size_mb": db_stats.get("size_mb", 0.0),
            "tropes": db_stats.get("tropes", 0),
            "examples": db_stats.get("examples", 0),
            "trope_relations": db_stats.get("trope_relations", 0),
            "work_tropes": db_stats.get("work_tropes", 0),
        },
        "ollama": {
            "queue_depth": max(0, crawl.get("crawled", 0) - db_stats.get("tropes", 0)),
            "avg_latency_ms": 0.0,
        },
    }
