"""Bridge that manages scraper lifecycle within the MCP server process."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from scraper.db import Config as ScraperConfig
from scraper.db import load_config
from scraper.extractor import Extractor as ScraperExtractor
from scraper.scheduler import CrawlScheduler

log = logging.getLogger(__name__)


class ScraperManager:
    """Starts/stops/monitors the crawler and extractor from within the MCP server."""

    def __init__(self, db_path: str, config: ScraperConfig | None = None) -> None:
        self.db_path = db_path
        self.config = config or load_config()
        self._scheduler: CrawlScheduler | None = None
        self._scheduler_lock = threading.Lock()
        self._extractor_running = False
        self._extractor_task: asyncio.Task | None = None

    def start_crawler(self) -> dict[str, Any]:
        with self._scheduler_lock:
            if self._scheduler and self._scheduler.is_running:
                return {"success": False, "message": "Crawler already running"}
            self._scheduler = CrawlScheduler(self.db_path, self.config)
            self._scheduler.start()
            return {
                "success": True,
                "message": f"Crawler started (session={self._scheduler._session_id})",
            }

    def stop_crawler(self) -> dict[str, Any]:
        with self._scheduler_lock:
            if not self._scheduler or not self._scheduler.is_running:
                return {"success": False, "message": "Crawler not running"}
            self._scheduler.stop()
            self._scheduler = None
            return {"success": True, "message": "Crawler stopped"}

    @property
    def crawler_running(self) -> bool:
        with self._scheduler_lock:
            return self._scheduler is not None and self._scheduler.is_running

    def get_status(self) -> dict[str, Any]:
        with self._scheduler_lock:
            crawler_status = {}
            if self._scheduler:
                try:
                    crawler_status = self._scheduler.get_status()
                except Exception as e:
                    crawler_status = {"error": str(e)}
            else:
                crawler_status = {
                    "running": False,
                    "crawl": {
                        "total": 0,
                        "pending": 0,
                        "crawled": 0,
                        "extracted": 0,
                        "failed": 0,
                        "blocked": 0,
                    },
                }

        return {
            "crawler": crawler_status,
            "extractor": {
                "running": self._extractor_running,
            },
        }

    async def start_extractor(self) -> dict[str, Any]:
        if self._extractor_running:
            return {"success": False, "message": "Extractor already running"}
        self._extractor_running = True
        self._extractor_task = asyncio.create_task(self._extractor_loop())
        return {"success": True, "message": "Extractor started"}

    async def stop_extractor(self) -> dict[str, Any]:
        self._extractor_running = False
        if self._extractor_task:
            self._extractor_task.cancel()
            try:
                await self._extractor_task
            except asyncio.CancelledError:
                pass
            self._extractor_task = None
        return {"success": True, "message": "Extractor stopped"}

    async def run_extraction_pass(self) -> dict[str, Any]:
        extractor = ScraperExtractor(self.db_path, self.config)
        try:
            result = await extractor.run_pass()
            return result
        finally:
            await extractor.close()

    async def _extractor_loop(self) -> None:
        while self._extractor_running:
            try:
                result = await self.run_extraction_pass()
                if result.get("success"):
                    log.info(f"Extraction pass: {result.get('extracted', 0)} pages")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Extraction loop error: {e}", exc_info=True)
            await asyncio.sleep(30)

    async def shutdown(self) -> None:
        self.stop_crawler()
        await self.stop_extractor()
