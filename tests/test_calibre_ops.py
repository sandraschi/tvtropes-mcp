"""Tests for src/tvtropes_mcp/calibre_ops.py."""

from __future__ import annotations

import os
import tempfile

from tvtropes_mcp.calibre_ops import (
    CALIBRE_DB_FILENAME,
    calibre_status,
    find_calibre_db,
    search_books,
)


def test_calibre_db_filename() -> None:
    assert CALIBRE_DB_FILENAME == "metadata.db"


def test_find_calibre_db_no_library() -> None:
    result = find_calibre_db()
    # May or may not find a real Calibre library depending on environment
    # This tests that it doesn't crash regardless
    assert result is None or result.exists()


def test_search_books_no_db() -> None:
    result = search_books(title="Test")
    assert result == []


def test_calibre_status_no_db() -> None:
    result = calibre_status()
    # May find a real Calibre library or not — either is valid
    assert "found" in result
    assert "book_count" in result


def test_search_books_with_empty_db() -> None:
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "metadata.db")
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, path TEXT, authors TEXT, series_index REAL)")
    conn.execute("INSERT INTO books VALUES (1, 'Test Book', '/path', 'Author', 1.0)")
    conn.commit()
    conn.close()

    result = search_books(title="Test", calibre_db=db_path)
    assert len(result) >= 1
    assert result[0]["title"] == "Test Book"

    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


def test_search_books_by_author() -> None:
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "metadata.db")
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, path TEXT, authors TEXT, series_index REAL)")
    conn.execute("INSERT INTO books VALUES (1, 'Elantris', '/e', 'Brandon Sanderson', 1.0)")
    conn.execute("INSERT INTO books VALUES (2, 'Mistborn', '/m', 'Brandon Sanderson', 1.0)")
    conn.commit()
    conn.close()

    result = search_books(author="Sanderson", calibre_db=db_path)
    assert len(result) == 2

    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


def test_search_books_limit() -> None:
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "metadata.db")
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, path TEXT, authors TEXT, series_index REAL)")
    for i in range(5):
        conn.execute("INSERT INTO books VALUES (?, ?, ?, ?, ?)", (i, f"Book {i}", f"/b{i}", "Author", 1.0))
    conn.commit()
    conn.close()

    result = search_books(title="Book", limit=3, calibre_db=db_path)
    assert len(result) == 3

    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


def test_lookup_tropes_for_book_imports() -> None:
    from tvtropes_mcp.calibre_ops import lookup_tropes_for_book

    assert callable(lookup_tropes_for_book)
