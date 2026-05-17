"""APScheduler-based crawl loop with daily budget enforcement."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any

from scraper.bootstrap import run_bootstrap
from scraper.crawler import TvtropesCrawler
from scraper.db import (
    Config,
    count_crawled,
    end_crawl_session,
    get_crawl_stats,
    load_config,
    mark_crawled,
    mark_failed,
    pop_pending,
    queue_urls,
    start_crawl_session,
)
from scraper.parser import extract_page_links

log = logging.getLogger(__name__)


class CrawlScheduler:
    """Manages the background crawl loop with politeness, budget, and session tracking."""

    def __init__(self, db_path: str, config: Config | None = None) -> None:
        self.db_path = db_path
        self.config = config or load_config()
        self.crawler = TvtropesCrawler(self.config)
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._session_id = str(uuid.uuid4())[:8]
        self._pages_crawled = 0
        self._pages_blocked = 0
        self._errors = 0
        self._bootstrapped = False

    def start(self) -> None:
        if self._running:
            log.warning("Crawler already running")
            return
        self._running = True
        self._stop_event.clear()
        self._pages_crawled = 0
        self._pages_blocked = 0
        self._errors = 0
        self._session_id = str(uuid.uuid4())[:8]
        start_crawl_session(self.db_path, self._session_id)
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="crawl-loop")
        self._thread.start()
        log.info(f"Crawl scheduler started (session={self._session_id})")

    def stop(self) -> None:
        log.info("Stopping crawl scheduler...")
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        self._thread = None
        end_crawl_session(
            self.db_path,
            self._session_id,
            self._pages_crawled,
            self._pages_blocked,
            self._errors,
        )
        self.crawler.close()
        log.info("Crawl scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._crawl_one()
            except Exception as e:
                self._errors += 1
                log.error(f"Crawl loop error: {e}", exc_info=True)
            time.sleep(1)

    def _crawl_one(self) -> None:
        if not self._bootstrapped:
            self._bootstrap()
            self._bootstrapped = True
            return

        page = pop_pending(self.db_path)
        if page is None:
            if count_crawled(self.db_path) > 0:
                log.debug("No pending pages — sleeping")
                time.sleep(30)
            else:
                log.info("No pending pages — re-bootstrapping")
                self._bootstrapped = False
            return

        url = page["url"]
        result = self.crawler.fetch(url)
        if result["blocked"]:
            from scraper.db import mark_blocked

            mark_blocked(self.db_path, page["id"])
            self._pages_blocked += 1
            log.warning(f"Blocked: {url}")
            time.sleep(60)
            return

        if not result["success"]:
            mark_failed(self.db_path, page["id"], result.get("status_code"))
            self._errors += 1
            return

        html = result["html"]
        content_hash = self.crawler.cache_html(url, html)
        mark_crawled(self.db_path, page["id"], content_hash, result["status_code"])
        self._pages_crawled += 1

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        links = extract_page_links(soup, url)
        if links:
            queue_urls(self.db_path, links)

        if self._pages_crawled % 100 == 0:
            stats = get_crawl_stats(self.db_path)
            log.info(f"Crawl progress: {stats}")

    def _bootstrap(self) -> None:
        log.info("Bootstrapping seed URLs...")
        result = run_bootstrap(self.db_path, self.config)
        log.info(f"Bootstrap complete: {result}")

    def get_status(self) -> dict[str, Any]:
        stats = get_crawl_stats(self.db_path)
        return {
            "running": self._running,
            "session_id": self._session_id,
            "pages_crawled_this_session": self._pages_crawled,
            "pages_blocked_this_session": self._pages_blocked,
            "errors_this_session": self._errors,
            "crawl": stats,
        }
