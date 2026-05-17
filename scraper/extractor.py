"""Ollama extraction pass — reads cached HTML, calls Ollama, writes structured data."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from scraper.crawler import TvtropesCrawler
from scraper.db import (
    Config,
    count_crawled,
    count_extracted,
    get_conn,
    insert_example,
    insert_relation,
    insert_work_trope,
    load_config,
    mark_extracted,
    upsert_trope,
)
from scraper.parser import classify_url

log = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are extracting structured data from a TVTropes wiki page.
Extract:
1. title: the trope or work name (string)
2. description: the main description paragraph (string, max 500 chars)
3. laconic: one-sentence summary if present (string or null)
4. examples: list of {{work_namespace, work_name, example_text}} (array, max 50)
5. related: list of {{relation_type: "SubTrope"|"SuperTrope"|"SisterTrope", namespace, page_name}} for trope links
6. categories: list of category names from the page footer

Respond ONLY with valid JSON. No markdown, no preamble."""


class Extractor:
    """Asynchronous Ollama extraction pass over crawled-but-not-extracted pages."""

    def __init__(self, db_path: str, config: Config | None = None) -> None:
        self.db_path = db_path
        self.config = config or load_config()
        self.crawler = TvtropesCrawler(self.config)
        self._client: httpx.AsyncClient | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._ollama_available: bool | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.ollama_timeout_s)
        return self._client

    async def _check_ollama(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        client = await self._ensure_client()
        try:
            r = await client.get(f"{self.config.ollama_url}/api/tags", timeout=5)
            if r.status_code == 200:
                models = r.json().get("models", [])
                available = any(m["name"].startswith(self.config.ollama_model) for m in models)
                if not available:
                    log.warning(f"Ollama model {self.config.ollama_model} not found")
                self._ollama_available = available
                return available
            log.warning(f"Ollama API returned {r.status_code}")
            self._ollama_available = False
            return False
        except Exception as e:
            log.warning(f"Ollama not available: {e}")
            self._ollama_available = False
            return False

    async def extract_page(self, html: str, url: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": False,
            "error": None,
            "title": None,
            "description": None,
            "laconic": None,
            "examples": [],
            "related": [],
            "categories": [],
        }

        client = await self._ensure_client()

        payload = {
            "model": self.config.ollama_model,
            "prompt": f"{EXTRACTION_PROMPT}\n\nURL: {url}\n\nPage HTML:\n{html[:8000]}",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 2048},
        }

        try:
            r = await client.post(
                f"{self.config.ollama_url}/api/generate",
                json=payload,
            )
            if r.status_code != 200:
                result["error"] = f"Ollama HTTP {r.status_code}"
                return result

            body = r.json()
            response_text = body.get("response", "")
            if not response_text:
                result["error"] = "Empty Ollama response"
                return result

            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                result["error"] = "Ollama returned invalid JSON"
                log.warning(f"Ollama JSON parse failed for {url}: {response_text[:200]}")
                return result

            result["success"] = True
            result["title"] = parsed.get("title")
            result["description"] = parsed.get("description")
            result["laconic"] = parsed.get("laconic")
            result["examples"] = parsed.get("examples", [])
            result["related"] = parsed.get("related", [])
            result["categories"] = parsed.get("categories", [])
            return result

        except httpx.TimeoutException:
            result["error"] = "Ollama timeout"
            return result
        except Exception as e:
            result["error"] = str(e)
            log.error(f"Ollama extraction error for {url}: {e}")
            return result

    async def run_pass(self) -> dict[str, Any]:
        if not await self._check_ollama():
            log.warning("Ollama unavailable — skipping extraction pass")
            return {"success": False, "reason": "ollama_unavailable", "extracted": 0}

        self._semaphore = asyncio.Semaphore(self.config.ollama_concurrent)

        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                "SELECT p.id, p.url, p.content_hash FROM pages p WHERE p.status='crawled' LIMIT 20"
            ).fetchall()

        if not rows:
            return {"success": True, "extracted": 0, "reason": "no_crawled_pages"}

        errors = 0

        async def _extract_one(row) -> bool:
            async with self._semaphore:
                page_id = row["id"]
                url = row["url"]
                content_hash = row["content_hash"]

                html = self.crawler.read_cached_html(content_hash)
                if html is None:
                    log.warning(f"Cache miss for {url} (hash={content_hash})")
                    return False

                result = await self.extract_page(html, url)
                if not result["success"]:
                    log.warning(f"Extraction failed for {url}: {result.get('error')}")
                    return False

                classified = classify_url(url)
                ns = classified[0] if classified else "Main"
                name = classified[1] if classified else "unknown"

                upsert_trope(
                    self.db_path,
                    ns,
                    name,
                    title=result["title"],
                    description=result.get("description"),
                    laconic=result.get("laconic"),
                )

                for ex in result.get("examples", []):
                    work_ns = ex.get("work_namespace")
                    work_name = ex.get("work_name")
                    example_text = ex.get("example_text")
                    if work_name and example_text:
                        insert_example(self.db_path, ns, name, work_ns, work_name, example_text)
                        if work_ns and work_name:
                            insert_work_trope(self.db_path, work_ns, work_name, ns, name)

                for rel in result.get("related", []):
                    rel_type = rel.get("relation_type", "Related")
                    to_ns = rel.get("namespace")
                    to_name = rel.get("page_name")
                    if to_ns and to_name:
                        insert_relation(self.db_path, ns, name, rel_type, to_ns, to_name)

                mark_extracted(self.db_path, page_id)
                return True

        tasks = [_extract_one(row) for row in rows]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        extracted = 0
        for r in results:
            if isinstance(r, Exception):
                errors += 1
                log.error(f"Extraction task error: {r}")
            elif r:
                extracted += 1
            else:
                errors += 1

        return {
            "success": True,
            "extracted": extracted,
            "errors": errors,
            "pending_extraction": count_crawled(self.db_path) - count_extracted(self.db_path),
        }

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
        self.crawler.close()
