"""Tests for scraper/parser.py — BeautifulSoup HTML parsing."""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from scraper.parser import (
    classify_url,
    extract_image_url,
    extract_laconic,
    extract_page_description,
    extract_page_links,
    extract_page_metadata,
    extract_page_title,
    extract_trope_links,
    is_cloudflare_blocked,
    is_work_namespace,
    parse_sitemap,
    split_trope_id,
)

SAMPLE_HTML = Path(__file__).resolve().parent / "sample_tvtropes_page.html"

SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsGun</loc></url>
  <url><loc>https://tvtropes.org/pmwiki/pmwiki.php/Main/RedHerring</loc></url>
  <url><loc>https://tvtropes.org/pmwiki/pmwiki.php/Film/Casablanca</loc></url>
</urlset>"""

BLOCK_PAGES_CF = [
    "Just a moment...",
    "Checking your browser before accessing",
    "cf-browser-verification",
    "Ray ID: abc-123",
    "Please enable JavaScript to continue.",
    "DDoS protection by Cloudflare",
    "cf_clearance cookie required",
]


@pytest.fixture
def soup() -> BeautifulSoup:
    html = SAMPLE_HTML.read_text(encoding="utf-8")
    return BeautifulSoup(html, "lxml")


def test_extract_page_title(soup: BeautifulSoup) -> None:
    title = extract_page_title(soup)
    assert title == "ChekhovsGun"


def test_extract_page_description(soup: BeautifulSoup) -> None:
    desc = extract_page_description(soup)
    assert desc is not None
    assert "unimportant element" in desc


def test_extract_laconic(soup: BeautifulSoup) -> None:
    laconic = extract_laconic(soup)
    assert laconic is not None
    assert "Every element" in laconic


def test_extract_page_links(soup: BeautifulSoup) -> None:
    links = extract_page_links(soup)
    # Should include all non-skip links from the sample
    assert len(links) >= 5
    urls = [lnk["url"] for lnk in links]
    assert any("Main/Foreshadowing" in u for u in urls), f"Missing Foreshadowing in {urls}"
    assert any("Main/RedHerring" in u for u in urls)
    assert any("Film/Casablanca" in u for u in urls)


def test_extract_page_links_skips_administrivia(soup: BeautifulSoup) -> None:
    links = extract_page_links(soup)
    namespaces = [lnk["namespace"] for lnk in links if lnk.get("namespace")]
    assert "Administrivia" not in namespaces


def test_extract_trope_links(soup: BeautifulSoup) -> None:
    links = extract_trope_links(soup)
    namespaces = [lnk["namespace"] for lnk in links]
    assert all(ns == "Main" for ns in namespaces)


def test_classify_url_valid() -> None:
    result = classify_url("https://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsGun")
    assert result == ("Main", "ChekhovsGun")


def test_classify_url_with_subpage() -> None:
    result = classify_url("https://tvtropes.org/pmwiki/pmwiki.php/Main/ActionHero/Tropes")
    assert result == ("Main", "ActionHero/Tropes")


def test_classify_url_external() -> None:
    result = classify_url("https://google.com/something")
    assert result is None


def test_classify_url_skip_namespace() -> None:
    result = classify_url("https://tvtropes.org/pmwiki/pmwiki.php/SandBox/TestPage")
    assert result is None


def test_is_work_namespace() -> None:
    assert is_work_namespace("Film")
    assert is_work_namespace("Series")
    assert is_work_namespace("Literature")
    assert not is_work_namespace("Main")
    assert not is_work_namespace("Administrivia")


def test_split_trope_id_with_namespace() -> None:
    assert split_trope_id("Main/ChekhovsGun") == ("Main", "ChekhovsGun")


def test_split_trope_id_without_namespace() -> None:
    assert split_trope_id("ChekhovsGun") == ("Main", "ChekhovsGun")


def test_is_cloudflare_blocked_true() -> None:
    for page in BLOCK_PAGES_CF:
        assert is_cloudflare_blocked(page), f"Should detect: {page}"


def test_is_cloudflare_blocked_false() -> None:
    assert not is_cloudflare_blocked("<html><body>Normal content</body></html>")


def test_parse_sitemap() -> None:
    urls = parse_sitemap(SITEMAP_XML)
    assert len(urls) == 3
    assert "Main/ChekhovsGun" in urls[0]


def test_extract_page_metadata(soup: BeautifulSoup) -> None:
    meta = extract_page_metadata(soup, "https://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsGun")
    assert meta["namespace"] == "Main"
    assert meta["page_name"] == "ChekhovsGun"
    assert meta["title"] == "ChekhovsGun"
    assert meta["is_work"] is False
    assert len(meta["page_links"]) >= 6


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/Portal", ("VideoGame", "Portal")),
        ("/pmwiki/pmwiki.php/Main/AntiHero", ("Main", "AntiHero")),
        ("/pmwiki/pmwiki.php?n=Main.AntiHero", None),
    ],
)
def test_classify_parametric(url: str, expected) -> None:
    assert classify_url(url) == expected


def test_extract_image_url_none(soup: BeautifulSoup) -> None:
    assert extract_image_url(soup) is None


def test_classify_url_www() -> None:
    result = classify_url("https://www.tvtropes.org/pmwiki/pmwiki.php/Main/Test")
    assert result == ("Main", "Test")
