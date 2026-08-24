"""MCP tool for querying the in-memory log store with filters."""

from __future__ import annotations

from typing import Any

from tvtropes_mcp.log_ring import get_recent


async def query_logs(
    source: str | None = None,
    level: str | None = None,
    search: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Query the in-memory log store. Filters by source, level, or keyword.

    ## Parameters
    - source: Filter by log source (logger name)
    - level: Filter by level (e.g. "error", "warning", "info")
    - search: Case-insensitive keyword search in message text
    - limit: Max entries to return (default 50, max 500)

    ## Return Format
    {"success": bool, "logs": list, "count": int, "filtered_by": dict}

    ## Examples
    await query_logs(level="error", limit=10)
    await query_logs(search="trope")
    """
    all_logs = get_recent(limit=5000)

    filtered = all_logs
    if source:
        filtered = [e for e in filtered if e.get("name") == source]
    if level:
        filtered = [e for e in filtered if e.get("level") == level]
    if search:
        search_lower = search.lower()
        filtered = [e for e in filtered if search_lower in e.get("message", "").lower()]

    truncated = filtered[-limit:] if len(filtered) > limit else filtered

    return {
        "success": True,
        "logs": truncated,
        "count": len(truncated),
        "total_matching": len(filtered),
        "filtered_by": {"source": source, "level": level, "search": search, "limit": limit},
    }
