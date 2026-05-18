"""Tests for scraper/extractor.py — mock-based extraction tests."""

from __future__ import annotations

import os
import tempfile

from scraper.db import Config, init_db


def test_extractor_ollama_check_no_server() -> None:
    """Extractor should gracefully handle missing Ollama server."""
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    init_db(db_path)
    config = Config(
        ollama_url="http://localhost:119999",  # definitely not running
        ollama_model="nonexistent-model",
        ollama_timeout_s=2.0,  # fast timeout
        cache_dir=os.path.join(tmp, "cache"),
        db_path=db_path,
    )
    import asyncio

    from scraper.extractor import Extractor

    extractor = Extractor(db_path, config)
    try:
        result = asyncio.run(extractor.run_pass())
        assert result.get("success") is False
        assert result.get("reason") == "ollama_unavailable"
    finally:
        asyncio.run(extractor.close())
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


def test_extraction_prompt_format() -> None:
    from scraper.extractor import EXTRACTION_PROMPT

    assert "Extract:" in EXTRACTION_PROMPT
    assert "title" in EXTRACTION_PROMPT
    assert "examples" in EXTRACTION_PROMPT
    assert "related" in EXTRACTION_PROMPT
    assert "JSON" in EXTRACTION_PROMPT
