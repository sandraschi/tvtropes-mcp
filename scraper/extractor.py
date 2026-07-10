"""Extraction pass — calls LLM (Ollama or OpenAI-compatible), writes structured data."""

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
4. examples: list of {work_namespace, work_name, example_text} (array, max 50)
5. related: list of {relation_type: "SubTrope"|"SuperTrope"|"SisterTrope", namespace, page_name} for trope links
6. categories: list of category names from the page footer

Respond ONLY with valid JSON. No markdown, no preamble."""


class Extractor:
    """Asynchronous LLM extraction pass over crawled-but-not-extracted pages.

    Supports two API modes (configured via Config.api_mode):
    - "ollama": Ollama native API (/api/generate, /api/tags, /api/embeddings)
    - "openai": OpenAI-compatible API (/v1/chat/completions, /v1/models, /v1/embeddings)
    """

    def __init__(self, db_path: str, config: Config | None = None) -> None:
        self.db_path = db_path
        self.config = config or load_config()
        self.crawler = TvtropesCrawler(self.config)
        self._client: httpx.AsyncClient | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._llm_available: bool | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = self.config.ollama_timeout_s
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def _check_llm(self) -> bool:
        if self._llm_available is not None:
            return self._llm_available
        client = await self._ensure_client()
        if self.config.api_mode == "openai":
            try:
                r = await client.get(f"{self.config.ollama_url}/v1/models", timeout=5)
                if r.status_code == 200:
                    models = r.json().get("data", [])
                    available = any(self.config.openai_chat_model in m.get("id", "") for m in models)
                    self._llm_available = available or True
                    return self._llm_available
                log.warning(f"OpenAI API returned {r.status_code}")
                self._llm_available = False
                return False
            except Exception as e:
                log.warning(f"OpenAI API not available: {e}")
                self._llm_available = False
                return False
        try:
            r = await client.get(f"{self.config.ollama_url}/api/tags", timeout=5)
            if r.status_code == 200:
                models = r.json().get("models", [])
                available = any(m["name"].startswith(self.config.ollama_model) for m in models)
                if not available:
                    log.warning(f"Ollama model {self.config.ollama_model} not found")
                self._llm_available = available
                return available
            log.warning(f"Ollama API returned {r.status_code}")
            self._llm_available = False
            return False
        except Exception as e:
            log.warning(f"Ollama not available: {e}")
            self._llm_available = False
            return False

    async def extract_page(self, html: str, url: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": False, "error": None,
            "title": None, "description": None, "laconic": None,
            "examples": [], "related": [], "categories": [],
        }
        client = await self._ensure_client()
        truncated = html[:8000]

        if self.config.api_mode == "openai":
            payload = {
                "model": self.config.openai_chat_model,
                "messages": [
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": f"URL: {url}\n\nPage HTML:\n{truncated}"},
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
            }
            try:
                r = await client.post(
                    f"{self.config.ollama_url}/v1/chat/completions",
                    json=payload,
                )
                if r.status_code != 200:
                    result["error"] = f"LLM HTTP {r.status_code}"
                    return result
                body = r.json()
                response_text = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not response_text:
                    result["error"] = "Empty LLM response"
                    return result
                try:
                    parsed = json.loads(response_text)
                except json.JSONDecodeError:
                    result["error"] = "LLM returned invalid JSON"
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
                result["error"] = "LLM timeout"
                return result
            except Exception as e:
                result["error"] = str(e)
                return result

        payload = {
            "model": self.config.ollama_model,
            "prompt": f"{EXTRACTION_PROMPT}\n\nURL: {url}\n\nPage HTML:\n{truncated}",
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
            return result

    async def run_pass(self) -> dict[str, Any]:
        use_html_fallback = not await self._check_llm()
        if use_html_fallback:
            log.info("LLM unavailable — using HTML extraction fallback")
        concurrent = self.config.ollama_concurrent
        self._semaphore = asyncio.Semaphore(concurrent)

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
                if not result["success"] and use_html_fallback:
                    from scraper.parser import extract_trope_from_html
                    result = extract_trope_from_html(html, url)
                if not result["success"]:
                    log.warning(f"Extraction failed for {url}: {result.get('error')}")
                    return False
                classified = classify_url(url)
                ns = classified[0] if classified else "Main"
                name = classified[1] if classified else "unknown"
                upsert_trope(self.db_path, ns, name, title=result["title"],
                             description=result.get("description"),
                             laconic=result.get("laconic"))
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
                try:
                    from tvtropes_mcp.vector_store import upsert_trope_embedding
                    await upsert_trope_embedding(
                        self.config.db_path,
                        {"namespace": ns, "page_name": name,
                         "title": result.get("title"), "description": result.get("description"),
                         "laconic": result.get("laconic")},
                        ollama_host=self.config.ollama_url,
                        api_mode=self.config.api_mode,
                    )
                except Exception as exc:
                    log.debug(f"Embedding skipped for {ns}/{name}: {exc}")
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
