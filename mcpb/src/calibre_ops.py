"""Calibre library integration — discover books and cross-reference with TVTropes."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CALIBRE_DB_FILENAME = "metadata.db"

_known_calibre_paths = [
    Path(os.environ.get("USERPROFILE", "")) / "Calibre Library",
    Path(os.environ.get("HOME", "")) / "Calibre Library",
    Path(os.environ.get("USERPROFILE", "")) / "Documents" / "Calibre Library",
    Path(os.environ.get("HOME", "")) / "Documents" / "Calibre Library",
]

CALIBRE_API_QUERY = """
SELECT b.id, b.title, b.path, b.authors, b.series_index
FROM books b
WHERE b.title LIKE ? ESCAPE '!'
ORDER BY b.title
LIMIT ?
"""

CALIBRE_BOOK_BY_AUTHOR = """
SELECT b.id, b.title, b.path, b.authors
FROM books b
WHERE b.authors LIKE ? ESCAPE '!'
ORDER BY b.title
LIMIT ?
"""

CALIBRE_BOOK_BY_ID = """
SELECT b.id, b.title, b.path, b.authors, b.series_index
FROM books b
WHERE b.id = ?
"""


def find_calibre_db() -> Path | None:
    for base in _known_calibre_paths:
        db = base / CALIBRE_DB_FILENAME
        if db.exists():
            log.info(f"Found Calibre library at {db}")
            return db
    # Check a few more common locations
    alt_bases = [
        Path("C:/Program Files/Calibre2"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "calibre",
    ]
    for base in alt_bases:
        db = base / CALIBRE_DB_FILENAME
        if db.exists():
            log.info(f"Found Calibre library at {db}")
            return db
    return None


def _connect(calibre_db: str | Path | None = None) -> sqlite3.Connection | None:
    if calibre_db is None:
        found = find_calibre_db()
        if found is None:
            return None
        calibre_db = found
    try:
        conn = sqlite3.connect(str(calibre_db))
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        log.warning(f"Failed to open Calibre DB: {e}")
        return None


def search_books(
    title: str | None = None,
    author: str | None = None,
    limit: int = 10,
    calibre_db: str | Path | None = None,
) -> list[dict[str, Any]]:
    conn = _connect(calibre_db)
    if conn is None:
        return []
    try:
        if title:
            pattern = f"%{title.replace('!', '!!').replace('%', '!%').replace('_', '!_')}%"
            rows = conn.execute(CALIBRE_API_QUERY, (pattern, limit)).fetchall()
        elif author:
            pattern = f"%{author.replace('!', '!!').replace('%', '!%').replace('_', '!_')}%"
            rows = conn.execute(CALIBRE_BOOK_BY_AUTHOR, (pattern, limit)).fetchall()
        else:
            return []
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        log.warning(f"Calibre query error: {e}")
        return []
    finally:
        conn.close()


def get_book(book_id: int, calibre_db: str | Path | None = None) -> dict[str, Any] | None:
    conn = _connect(calibre_db)
    if conn is None:
        return None
    try:
        row = conn.execute(CALIBRE_BOOK_BY_ID, (book_id,)).fetchone()
        if row is None:
            return None
        return dict(row)
    except sqlite3.Error as e:
        log.warning(f"Calibre get_book error: {e}")
        return None
    finally:
        conn.close()


def lookup_tropes_for_book(
    book_title: str,
    db_path: str | None = None,
    calibre_db: str | Path | None = None,
) -> dict[str, Any]:
    from tvtropes_mcp.db import trope_search, work_tropes

    # Try direct title match in Literature/ namespace
    lit_tropes = work_tropes(f"Literature/{_normalize_title(book_title)}", db_path=db_path)

    # Also search tropes by title keywords
    search_query = book_title
    fts_results = trope_search(search_query, limit=10, db_path=db_path)

    return {
        "success": True,
        "book_title": book_title,
        "direct_literature_match": lit_tropes,
        "fts_results": fts_results,
        "total_direct": len(lit_tropes),
        "total_fts": len(fts_results),
    }


def _normalize_title(title: str) -> str:
    return title.replace(" ", "").replace(":", "").replace("'", "")


def calibre_status(calibre_db: str | Path | None = None) -> dict[str, Any]:
    conn = _connect(calibre_db)
    if conn is None:
        return {"found": False, "library_path": None, "book_count": 0}
    try:
        count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        return {
            "found": True,
            "library_path": str(conn.execute("PRAGMA database_list").fetchone()[2]),
            "book_count": count,
        }
    except sqlite3.Error as e:
        return {"found": False, "error": str(e), "book_count": 0}
    finally:
        conn.close()
