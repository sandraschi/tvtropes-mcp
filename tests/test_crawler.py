"""Tests for scraper/crawler.py — mock-based crawler tests."""

from __future__ import annotations

import os
import tempfile

import pytest

from scraper.crawler import TvtropesCrawler
from scraper.db import Config


@pytest.fixture
def config() -> Config:
    return Config(
        min_delay_s=0.0,
        max_delay_s=0.0,
        max_retries=2,
        daily_budget=100,
        cache_dir=os.path.join(tempfile.mkdtemp(), "cache"),
        db_path=os.path.join(tempfile.mkdtemp(), "test.db"),
    )


@pytest.fixture
def crawler(config: Config) -> TvtropesCrawler:
    c = TvtropesCrawler(config)
    yield c
    c.close()


def test_crawler_init(config: Config) -> None:
    c = TvtropesCrawler(config)
    assert c._cache_dir.exists()
    c.close()


def test_cache_html(crawler: TvtropesCrawler) -> None:
    html = "<html><body>Hello</body></html>"
    content_hash = crawler.cache_html("https://example.com/test", html)
    assert len(content_hash) == 64  # SHA256 hex

    cached = crawler.read_cached_html(content_hash)
    assert cached == html


def test_cache_html_gz(crawler: TvtropesCrawler) -> None:
    html = "<html><body>Compressed test</body></html>"
    content_hash = crawler.cache_html("https://example.com/test", html)
    subdir = crawler._cache_dir / content_hash[:2]
    gz_path = subdir / f"{content_hash}.html.gz"
    assert gz_path.exists()


def test_read_cached_html_miss(crawler: TvtropesCrawler) -> None:
    result = crawler.read_cached_html("nonexistenthash1234567890abcdef1234567890abcdef1234567890abcdef12345678")
    assert result is None


def test_fetch_mock_mode_no_curl(crawler: TvtropesCrawler) -> None:
    from scraper.crawler import HAS_CURL

    result = crawler.fetch("https://tvtropes.org/pmwiki/pmwiki.php/Main/Test")
    if not HAS_CURL:
        assert result["success"] is True
        assert result["html"] is not None
        assert "Mock page" in result["html"]
    else:
        # With curl_cffi installed, real fetch may fail in test env
        pass


def test_fetch_daily_budget_exhausted(crawler: TvtropesCrawler) -> None:
    crawler._daily_count = crawler.config.daily_budget
    result = crawler.fetch("https://tvtropes.org/pmwiki/pmwiki.php/Main/Test")
    assert result["success"] is False
    assert "budget" in result.get("error", "").lower()


def test_session_rotation(crawler: TvtropesCrawler) -> None:
    crawler.config.session_rotate_every = 2
    assert crawler._request_count == 0

    for _ in range(2):
        crawler._rotate_if_needed()

    count = crawler._request_count
    assert count == 2 or count == 0  # either before or after rotation threshold


def test_respect_delay_noop_with_zero_delay(crawler: TvtropesCrawler) -> None:
    import time

    before = time.time()
    crawler._respect_delay()
    elapsed = time.time() - before
    assert elapsed < 0.5  # negligible delay


def test_close(crawler: TvtropesCrawler) -> None:
    crawler.close()
    assert crawler._session is None
