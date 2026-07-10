"""Bootstrap seed URL queue from sitemap.xml and namespace index pages."""

from __future__ import annotations

import logging
from typing import Any

from scraper.crawler import TvtropesCrawler
from scraper.db import Config, count_pending, queue_urls
from scraper.parser import TVTROPES_BASE, extract_page_links, is_cloudflare_blocked, parse_sitemap

log = logging.getLogger(__name__)

# Multiple sitemap URLs to try in order — /sitemap.xml now returns 403 from Cloudflare.
SITEMAP_URLS = [
    f"{TVTROPES_BASE}/sitemap.xml",
    f"{TVTROPES_BASE}/sitemap_index.xml",
    f"{TVTROPES_BASE}/page-sitemap.xml",
]

NAMESPACE_INDEX_PAGES = [
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/Tropes",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/Film",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/Series",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/Anime",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/Literature",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/VideoGame",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/WesternAnimation",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/Music",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/ComicBook",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/Webcomic",
    f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/WebOriginal",
]


def _queue_entries(db_path: str, urls: list[str]) -> int:
    """Classify parsed sitemap URLs and queue them into DB."""
    from scraper.parser import classify_url

    entries = []
    for url in urls:
        classified = classify_url(url)
        if classified:
            ns, name = classified
            entries.append({"url": url, "namespace": ns, "page_name": name})
    if not entries:
        return 0
    return queue_urls(db_path, entries)


def seed_from_sitemap(db_path: str, crawler: TvtropesCrawler) -> int:
    """Seed URL queue from sitemap with multi-strategy fallback.

    Strategy order:
      1. Try ``/sitemap.xml``, ``/sitemap_index.xml``, ``/page-sitemap.xml``
         on tvtropes.org directly (fastest path).
      2. Wayback Machine CDX/archive for recent sitemap snapshots.
      3. Parse outgoing links from the main page.
    """
    # -- Strategy 1: direct sitemap URLs on tvtropes.org --
    for sm_url in SITEMAP_URLS:
        result = crawler.fetch(sm_url)
        if result["success"]:
            urls = parse_sitemap(result["html"])
            if urls:
                log.info("Found %d URLs from sitemap: %s", len(urls), sm_url)
                return _queue_entries(db_path, urls)
            log.info("Sitemap %s returned empty URL list", sm_url)
        else:
            log.info("Sitemap attempt failed for %s: %s", sm_url, result.get("error"))

    # -- Strategy 2: Wayback Machine archive --
    # Note: using httpx directly (not crawler) since Wayback Machine has no Cloudflare.
    _wayback_urls = [
        "https://web.archive.org/web/2025/https://tvtropes.org/sitemap.xml",
        "https://web.archive.org/web/2024/https://tvtropes.org/sitemap.xml",
        "https://web.archive.org/web/2023/https://tvtropes.org/sitemap.xml",
    ]
    import httpx

    for wb_url in _wayback_urls:
        try:
            resp = httpx.get(
                wb_url,
                timeout=15,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                },
            )
            if resp.status_code == 200 and not is_cloudflare_blocked(resp.text):
                urls = parse_sitemap(resp.text)
                if urls:
                    log.info("Found %d URLs from Wayback Machine: %s", len(urls), wb_url)
                    return _queue_entries(db_path, urls)
            log.info(
                "Wayback Machine attempt returned HTTP %d for %s",
                resp.status_code,
                wb_url,
            )
        except Exception as exc:
            log.info("Wayback Machine attempt failed for %s: %s", wb_url, exc)

    # -- Strategy 3: main page link parsing --
    try:
        result = crawler.fetch(TVTROPES_BASE)
        if result["success"]:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(result["html"], "lxml")
            links = extract_page_links(soup, TVTROPES_BASE)
            entries = [link for link in links if link.get("namespace") and link.get("page_name")]
            if entries:
                added = queue_urls(db_path, entries)
                log.info("Seeded %d URLs from main page link parsing", added)
                return added
            log.info("Main page link parsing found no valid entries")
        else:
            log.info("Main page fetch failed: %s", result.get("error"))
    except Exception as exc:
        log.info("Main page link parsing failed: %s", exc)

    log.error(
        "All sitemap strategies failed — tvtropes.org may be unreachable or fully blocked"
    )
    return 0


def seed_from_namespace_indexes(db_path: str, crawler: TvtropesCrawler) -> int:
    total_added = 0
    for url in NAMESPACE_INDEX_PAGES:
        result = crawler.fetch(url)
        if not result["success"]:
            log.warning(f"Failed to fetch index {url}: {result.get('error')}")
            continue
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(result["html"], "lxml")
        links = extract_page_links(soup, url)
        entries = []
        for link in links:
            if link.get("namespace") and link.get("page_name"):
                entries.append(link)
        if entries:
            added = queue_urls(db_path, entries)
            total_added += added
            log.info(f"Seeded {added} URLs from {url}")
    return total_added


def run_bootstrap(
    db_path: str,
    config: Config | None = None,
) -> dict[str, Any]:
    if config is None:
        config = Config()
    crawler = TvtropesCrawler(config)
    try:
        existing = count_pending(db_path)
        sitemap_added = seed_from_sitemap(db_path, crawler)
        index_added = seed_from_namespace_indexes(db_path, crawler)
        total = count_pending(db_path)
        return {
            "success": True,
            "existing_before": existing,
            "sitemap_added": sitemap_added,
            "index_added": index_added,
            "total_pending": total,
        }
    finally:
        crawler.close()
