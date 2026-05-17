"""Bootstrap seed URL queue from sitemap.xml and namespace index pages."""

from __future__ import annotations

import logging
from typing import Any

from scraper.crawler import TvtropesCrawler
from scraper.db import Config, count_pending, queue_urls
from scraper.parser import TVTROPES_BASE, extract_page_links, parse_sitemap

log = logging.getLogger(__name__)

SITEMAP_URL = f"{TVTROPES_BASE}/sitemap.xml"

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


def seed_from_sitemap(db_path: str, crawler: TvtropesCrawler) -> int:
    result = crawler.fetch(SITEMAP_URL)
    if not result["success"]:
        log.warning(f"Failed to fetch sitemap: {result.get('error')}")
        return 0
    urls = parse_sitemap(result["html"])
    log.info(f"Found {len(urls)} URLs in sitemap")
    entries = []
    for url in urls:
        from scraper.parser import classify_url

        classified = classify_url(url)
        if classified:
            ns, name = classified
            entries.append({"url": url, "namespace": ns, "page_name": name})
    if not entries:
        return 0
    added = queue_urls(db_path, entries)
    log.info(f"Seeded {added} URLs from sitemap (out of {len(entries)} parsed)")
    return added


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
