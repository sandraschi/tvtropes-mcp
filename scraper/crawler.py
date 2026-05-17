"""TVTropes crawler — curl_cffi-based fetcher with politeness, block detection, and cache."""

from __future__ import annotations

import gzip
import hashlib
import logging
import random
import time
from pathlib import Path
from typing import Any

from scraper.db import Config
from scraper.parser import TVTROPES_BASE, is_cloudflare_blocked

log = logging.getLogger(__name__)

try:
    from curl_cffi import requests as curl_requests

    HAS_CURL = True
except ImportError:
    HAS_CURL = False
    log.warning("curl_cffi not available — crawler will use mock mode")


class TvtropesCrawler:
    """Polite TVTropes scraper using curl_cffi for Chrome TLS impersonation."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._session = None
        self._request_count = 0
        self._cache_dir = Path(config.cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_fetch_time = 0.0
        self._daily_count = 0
        self._daily_date = time.strftime("%Y-%m-%d")

    def _ensure_session(self):
        if self._session is None:
            if HAS_CURL:
                self._session = curl_requests.Session(
                    impersonate="chrome120",
                    default_headers=False,
                )
            log.info("Created new curl_cffi session")

    def _apply_headers(self):
        if self._session is None:
            return
        urls = [
            TVTROPES_BASE,
            f"{TVTROPES_BASE}/pmwiki/pmwiki.php/Main/Tropes",
        ]
        self._session.headers.update(
            {
                "Accept": self.config.accept,
                "Accept-Language": self.config.accept_language,
                "Accept-Encoding": self.config.accept_encoding,
                "Referer": random.choice(urls),  # noqa: S311
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Sec-CH-UA": '"Google Chrome";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"Windows"',
            }
        )

    def _respect_delay(self):
        elapsed = time.time() - self._last_fetch_time
        delay = random.uniform(self.config.min_delay_s, self.config.max_delay_s)  # noqa: S311
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def _rotate_if_needed(self):
        self._request_count += 1
        if self._request_count >= self.config.session_rotate_every:
            self._session = None
            self._request_count = 0
            log.info("Session rotation threshold reached — rotating")
            self._ensure_session()

    def _check_daily_budget(self) -> bool:
        today = time.strftime("%Y-%m-%d")
        if today != self._daily_date:
            self._daily_count = 0
            self._daily_date = today
        return self._daily_count < self.config.daily_budget

    def fetch(self, url: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": False,
            "html": None,
            "status_code": None,
            "blocked": False,
            "error": None,
        }

        if not self._check_daily_budget():
            result["error"] = "Daily budget exhausted"
            return result

        self._respect_delay()
        self._ensure_session()
        self._apply_headers()

        try:
            if HAS_CURL:
                resp = self._session.get(url, timeout=30)
                result["status_code"] = resp.status_code
                html = resp.text
            else:
                log.info(f"[MOCK] Would fetch: {url}")
                html = f"<html><body><p>Mock page for {url}</p></body></html>"
                result["status_code"] = 200

            if is_cloudflare_blocked(html):
                result["blocked"] = True
                result["error"] = "Cloudflare block page detected"
                log.warning(f"Blocked by Cloudflare: {url}")
                return result

            if result["status_code"] != 200:
                result["error"] = f"HTTP {result['status_code']}"
                log.warning(f"HTTP {result['status_code']} for {url}")
                return result

            result["success"] = True
            result["html"] = html
            self._daily_count += 1
            self._last_fetch_time = time.time()
            self._rotate_if_needed()
            return result

        except Exception as e:
            result["error"] = str(e)
            log.error(f"Fetch failed for {url}: {e}")
            return result

    def cache_html(self, url: str, html: str) -> str:
        content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
        subdir = self._cache_dir / content_hash[:2]
        subdir.mkdir(parents=True, exist_ok=True)
        path = subdir / f"{content_hash}.html.gz"
        if not path.exists():
            with gzip.open(path, "wt", encoding="utf-8") as f:
                f.write(html)
        return content_hash

    def read_cached_html(self, content_hash: str) -> str | None:
        subdir = self._cache_dir / content_hash[:2]
        path = subdir / f"{content_hash}.html.gz"
        if not path.exists():
            return None
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()

    def close(self):
        self._session = None
