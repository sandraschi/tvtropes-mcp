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

_SCRAPING_API_URLS = {
    "scrapieapi": "http://api.scraperapi.com",
    "scrapingbee": "https://app.scrapingbee.com/api/v1",
    "zenrows": "https://api.zenrows.com/v1",
}

_SCRAPING_API_PARAMS = {
    "scrapieapi": {"api_key": None, "url": None},
    "scrapingbee": {"api_key": None, "url": None},
    "zenrows": {"apikey": None, "url": None},
}

# Chrome version to impersonate. Must match a version curl_cffi supports.
# `chrome` = latest stable. Specific version = that exact TLS fingerprint.
CHROME_IMPERSONATE = "chrome131"  # latest stable as of 2026-05


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
        self._warmed_up = False

    def _ensure_session(self):
        if self._session is None:
            if HAS_CURL:
                self._session = curl_requests.Session(
                    impersonate=CHROME_IMPERSONATE,
                    default_headers=False,
                )
            log.info("Created new curl_cffi session")
            self._warmed_up = False

    def _apply_headers(self):
        if self._session is None:
            return
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-AT,de;q=0.9,en;q=0.8,ja;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "max-age=0",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not?A_Brand";v="24"',
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

    def warmup(self) -> bool:
        """Fetch the TVTropes homepage to establish cookies and a browsing context.

        A brand-new session that immediately fetches a deep page (e.g.
        Anime/Planetarian) is suspicious. Real users load the homepage first,
        get cookies set, then navigate. Call this before the first real fetch.
        Returns True if warmup succeeded.
        """
        if self._warmed_up:
            return True
        if not HAS_CURL:
            self._warmed_up = True
            return True

        self._ensure_session()
        self._apply_headers()

        try:
            # First request: no referer, Sec-Fetch-Site: none (direct navigation)
            self._session.headers.update(
                {
                    "Referer": TVTROPES_BASE,
                    "Sec-Fetch-Site": "none",
                }
            )
            resp = self._session.get(TVTROPES_BASE, timeout=30)
            if is_cloudflare_blocked(resp.text):
                log.warning("Warmup blocked by Cloudflare — TVTropes may be behind enhanced protection")
                self._warmed_up = False
                return False
            if resp.status_code == 200:
                log.info("Session warmup successful (homepage loaded)")
                self._warmed_up = True
                self._last_fetch_time = time.time()
                # Switch to same-origin for subsequent requests
                self._session.headers.update(
                    {
                        "Referer": TVTROPES_BASE,
                        "Sec-Fetch-Site": "same-origin",
                    }
                )
                return True
            log.warning(f"Warmup returned HTTP {resp.status_code}")
            return False
        except Exception as e:
            log.warning(f"Warmup failed: {e}")
            return False

    def _fetch_via_scraping_api(self, url: str) -> dict[str, Any]:
        """Fetch a page through a third-party scraping API to bypass Cloudflare."""
        import httpx

        result: dict[str, Any] = {
            "success": False,
            "html": None,
            "status_code": None,
            "blocked": False,
            "error": None,
        }

        provider = self.config.scraping_api_provider
        api_key = self.config.scraping_api_key
        base_url = _SCRAPING_API_URLS.get(provider)
        if not base_url or not api_key:
            result["error"] = f"Invalid scraping API config: provider={provider}, key_set={bool(api_key)}"
            return result

        params = dict(_SCRAPING_API_PARAMS[provider])
        for k in params:
            if params[k] is None:
                params[k] = api_key if k in ("api_key", "apikey") else url

        try:
            resp = httpx.get(base_url, params=params, timeout=60, follow_redirects=True)
            result["status_code"] = resp.status_code
            html = resp.text

            if is_cloudflare_blocked(html):
                result["blocked"] = True
                result["error"] = "Cloudflare block page detected (scraping API returned block page)"
                log.warning(f"Scraping API returned block page for {url}")
                return result

            if result["status_code"] != 200:
                result["error"] = f"HTTP {result['status_code']} (scraping API)"
                log.warning(f"Scraping API HTTP {result['status_code']} for {url}")
                return result

            result["success"] = True
            result["html"] = html
            return result

        except Exception as e:
            result["error"] = f"Scraping API error: {e}"
            log.error(f"Scraping API fetch failed for {url}: {e}")
            return result

    def _fetch_via_obscura(self, url: str) -> dict[str, Any] | None:
        """Fetch page via Obscura engine with stealth V8 JS execution when Cloudflare blocks standard fetch."""
        try:
            import sys
            from pathlib import Path

            obscura_mcp_path = Path("D:/Dev/repos/obscura-mcp/src")
            if obscura_mcp_path.exists() and str(obscura_mcp_path) not in sys.path:
                sys.path.insert(0, str(obscura_mcp_path))

            from obscura_mcp.server import fetch_with_obscura

            html = fetch_with_obscura(url, dump="html", stealth=True, timeout=35)
            if html and not is_cloudflare_blocked(html):
                log.info(f"Obscura stealth fetch succeeded for {url}")
                return {"success": True, "html": html, "status_code": 200, "blocked": False, "error": None}
        except Exception as e:
            log.warning(f"Obscura fetch fallback failed for {url}: {e}")
        return None

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

        # Route through scraping API when enabled (bypasses Cloudflare)
        if self.config.scraping_api_enabled:
            return self._fetch_via_scraping_api(url)

        # Auto-warmup on first real fetch if not already warmed up
        if not self._warmed_up and HAS_CURL:
            warmed = self.warmup()
            if not warmed:
                # Try Obscura stealth fallback before giving up on warmup block
                obs_res = self._fetch_via_obscura(url)
                if obs_res:
                    return obs_res
                result["blocked"] = True
                result["error"] = "Cloudflare block page detected during session warmup"
                result["note"] = "Session warmup failed. Retrying with backoff."
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

            if is_cloudflare_blocked(html) or result["status_code"] in (403, 429):
                log.warning(
                    f"Blocked or rate-limited ({result['status_code']}): {url} — attempting Obscura stealth fallback"
                )
                obs_res = self._fetch_via_obscura(url)
                if obs_res:
                    return obs_res
                result["blocked"] = True
                result["error"] = "Cloudflare block page detected"
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
