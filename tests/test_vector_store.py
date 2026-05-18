"""Tests for src/tvtropes_mcp/vector_store.py — LanceDB integration."""

from __future__ import annotations

import os
import tempfile

from tvtropes_mcp.vector_store import (
    _make_text,
    count_vectors,
    ensure_table,
    open_db,
)


def test_lancedb_connect() -> None:
    tmp = tempfile.mkdtemp()
    db = open_db(tmp)
    assert db is not None
    db_path = os.path.join(tmp, "lancedb")
    assert os.path.isdir(db_path)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def test_ensure_table_creates() -> None:
    tmp = tempfile.mkdtemp()
    table = ensure_table(tmp)
    assert table.name == "tropes"
    assert table.count_rows() == 0
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def test_count_vectors_empty() -> None:
    tmp = tempfile.mkdtemp()
    assert count_vectors(tmp) == 0
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def test_make_text_with_all_fields() -> None:
    trope = {
        "namespace": "Main",
        "page_name": "ChekhovsGun",
        "title": "Chekhov's Gun",
        "description": "A dramatic principle.",
        "laconic": "Every element must be necessary.",
    }
    text = _make_text(trope)
    assert "Chekhov's Gun" in text
    assert "A dramatic principle" in text
    assert "Every element must be necessary" in text


def test_make_text_minimal() -> None:
    trope = {"namespace": "Main", "page_name": "TestTrope"}
    text = _make_text(trope)
    assert text == "TestTrope"


def test_semantic_search_imports() -> None:
    from tvtropes_mcp.vector_store import semantic_search, upsert_trope_embedding
    assert callable(semantic_search)
    assert callable(upsert_trope_embedding)


def test_get_embedding_no_ollama() -> None:
    import asyncio

    from tvtropes_mcp.vector_store import get_embedding
    result = asyncio.run(get_embedding("test", ollama_host="http://localhost:19999"))
    assert result is None
