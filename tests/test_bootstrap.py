"""Tests for scraper/bootstrap.py — mock-based bootstrap tests."""

from __future__ import annotations

import os
import tempfile

from scraper.bootstrap import (
    NAMESPACE_INDEX_PAGES,
    SITEMAP_URLS,
    run_bootstrap,
)
from scraper.db import Config, init_db


def test_bootstrap_runs_with_empty_db() -> None:
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    init_db(db_path)
    config = Config(
        min_delay_s=0.0,
        max_delay_s=0.0,
        daily_budget=100,
        cache_dir=os.path.join(tmp, "cache"),
        db_path=db_path,
    )
    result = run_bootstrap(db_path, config)
    assert result["success"] is True
    # In mock mode (no curl_cffi), bootstrap won't actually fetch sitemap but won't crash
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


def test_sitemap_urls_list() -> None:
    assert len(SITEMAP_URLS) >= 3
    assert SITEMAP_URLS[0] == "https://tvtropes.org/sitemap.xml"
    assert all("tvtropes.org" in url for url in SITEMAP_URLS)


def test_namespace_index_pages() -> None:
    assert len(NAMESPACE_INDEX_PAGES) >= 10
    assert all("Main/" in url for url in NAMESPACE_INDEX_PAGES)
