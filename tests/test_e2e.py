"""End-to-end tests: FastAPI app, MCP proxy, and all tool endpoints against seeded DB."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from scraper.db import queue_urls, get_crawl_stats


# ─── Health & Status ─────────────────────────────────────────────

class TestHealth:
    def test_health(self, client: TestClient) -> None:
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "tvtropes-mcp"

    def test_root(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["service"] == "tvtropes-mcp"
        assert data["mcp_http"] == "http://127.0.0.1:10964/mcp"
        assert "stdio" in data["transports"]
        assert "streamable_http" in data["transports"]

    def test_manifest(self, client: TestClient) -> None:
        r = client.get("/.well-known/mcp/manifest.json")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "tvtropes-mcp"
        assert "transports" in data

    def test_tools_list(self, client: TestClient) -> None:
        r = client.get("/api/tools")
        assert r.status_code == 200
        data = r.json()
        assert len(data["tools"]) == 11
        assert "trope_search" in data["tools"]
        assert "calibre_status" in data["tools"]

    def test_status(self, client: TestClient) -> None:
        r = client.get("/api/status")
        assert r.status_code == 200
        data = r.json()
        assert data["db"]["tropes"] >= 8
        assert data["db"]["examples"] >= 3
        assert "scraper" in data

    def test_mcp_tools_schemas(self, client: TestClient) -> None:
        r = client.get("/api/mcp/tools")
        assert r.status_code == 200
        tools = r.json()
        names = [t["name"] for t in tools]
        assert "trope_search" in names
        assert "trope_get" in names
        assert all("inputSchema" in t for t in tools)


# ─── MCP Tool Proxy ──────────────────────────────────────────────

class TestTropeSearch:
    def test_search_found(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "trope_search", "args": {"query": "dramatic", "limit": 5}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["total"] >= 1
        assert any("ChekhovsGun" in r["id"] for r in data["results"])

    def test_search_not_found(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "trope_search", "args": {"query": "zzzznonexistent", "limit": 5}})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0

    def test_search_fuzzy(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "trope_search", "args": {"query": "misleading", "limit": 5}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert any("RedHerring" in r["id"] for r in data["results"])


class TestTropeGet:
    def test_get_existing(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "trope_get", "args": {"trope_id": "Main/ChekhovsGun"}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        trope = data["trope"]
        assert trope["name"] == "Chekhov's Gun"
        assert trope["description"] is not None
        assert len(trope["examples"]) >= 2  # Casablanca + BreakingBad

    def test_get_with_relations(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "trope_get", "args": {"trope_id": "Main/AntiHero"}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        trope = data["trope"]
        assert len(trope["sub_tropes"]) == 1
        assert len(trope["super_tropes"]) == 1
        assert len(trope["sister_tropes"]) == 1
        assert len(trope["related_tropes"]) == 1

    def test_get_not_found(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "trope_get", "args": {"trope_id": "Main/Nonexistent"}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False
        assert data["trope"] is None


class TestWorkTropes:
    def test_work_with_tropes(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "work_tropes", "args": {"work_id": "Film/Casablanca"}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["count"] >= 2  # ChekhovsGun + MacGuffin

    def test_work_no_tropes(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "work_tropes", "args": {"work_id": "Film/Nonexistent"}})
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 0


class TestTropeExamples:
    def test_examples_all(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "trope_examples", "args": {"trope_id": "Main/ChekhovsGun", "limit": 10}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["count"] >= 2

    def test_examples_filtered(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={
            "name": "trope_examples",
            "args": {"trope_id": "Main/ChekhovsGun", "namespace": "Film", "limit": 10},
        })
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 1
        assert all(e["work_ns"] == "Film" for e in data["examples"])

    def test_examples_no_results(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={
            "name": "trope_examples",
            "args": {"trope_id": "Main/Nonexistent", "limit": 5},
        })
        assert r.status_code == 200
        assert r.json()["count"] == 0


class TestRelatedTropes:
    def test_related_found(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "related_tropes", "args": {"trope_id": "Main/AntiHero"}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert len(data["sub_tropes"]) == 1
        assert data["sub_tropes"][0]["page_name"] == "ByronicHero"

    def test_related_empty(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "related_tropes", "args": {"trope_id": "Main/ChekhovsGun"}})
        assert r.status_code == 200
        data = r.json()
        assert len(data["sub_tropes"]) == 0


class TestNamespaceList:
    def test_namespaces(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "namespace_list", "args": {}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        ns = {n["namespace"]: n["page_count"] for n in data["namespaces"]}
        assert ns.get("Main", 0) >= 6
        assert ns.get("Film", 0) >= 1
        assert ns.get("Series", 0) >= 1


class TestRandomTrope:
    def test_random(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "random_trope", "args": {}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["trope"] is not None
        assert "id" in data["trope"]


class TestScraperStatus:
    def test_status(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "scraper_status", "args": {}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["db"]["tropes"] >= 8
        assert data["db"]["examples"] >= 3


class TestTropeLookupByTitle:
    def test_lookup(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "trope_lookup_by_title", "args": {"title": "Casablanca"}})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["book_title"] == "Casablanca"


class TestMCPErrors:
    def test_missing_name(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "", "args": {}})
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_invalid_tool(self, client: TestClient) -> None:
        r = client.post("/api/mcp/tool", json={"name": "nonexistent_tool", "args": {}})
        assert r.status_code == 200
        data = r.json()
        assert "error" in data or data.get("success") is False


# ─── Scraper API ─────────────────────────────────────────────────

class TestScraperAPI:
    def test_scraper_status_endpoint(self, client: TestClient) -> None:
        r = client.get("/api/scraper/status")
        assert r.status_code == 200
        data = r.json()
        assert "crawler" in data
        assert data["crawler"]["running"] is False

    def test_scraper_start_stop(self, client: TestClient) -> None:
        r = client.post("/api/scraper/start")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

        r = client.post("/api/scraper/stop")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True


# ─── Full Pipeline: Queue → Crawl → Extract → Query ──────────────

class TestScraperPipeline:
    """End-to-end pipeline test: seed URLs → mock crawl → mark extracted → query.

    This tests the full data path without network or Ollama by manually
    stepping through each phase and verifying DB state after each step.
    """

    def test_full_pipeline(self, db_path: str) -> None:
        from scraper.db import (
            get_crawl_stats,
            mark_crawled,
            mark_extracted,
            pop_pending,
            queue_urls,
        )
        from scraper.db import (
            insert_example,
            insert_relation,
            insert_work_trope,
            upsert_trope,
        )
        from tvtropes_mcp.db import trope_search, trope_get, work_tropes

        # Phase 1: Seed queue
        urls = [
            {"url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsGun", "namespace": "Main", "page_name": "ChekhovsGun"},
            {"url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/RedHerring", "namespace": "Main", "page_name": "RedHerring"},
        ]
        added = queue_urls(db_path, urls)
        assert added == 2
        stats = get_crawl_stats(db_path)
        assert stats["pending"] == 2

        # Phase 2: Pop and crawl
        page1 = pop_pending(db_path)
        assert page1 is not None
        mark_crawled(db_path, page1["id"], "hash_chekhovsgun", 200)
        stats = get_crawl_stats(db_path)
        assert stats["crawled"] == 1

        page2 = pop_pending(db_path)
        assert page2 is not None
        mark_crawled(db_path, page2["id"], "hash_redherring", 200)
        stats = get_crawl_stats(db_path)
        assert stats["crawled"] == 2
        assert stats["pending"] == 0

        # Phase 3: Extract (simulate Ollama output)
        upsert_trope(
            db_path, "Main", "ChekhovsGun",
            title="Chekhov's Gun",
            description="A dramatic principle.",
            laconic="Every element must be necessary.",
        )
        insert_example(db_path, "Main", "ChekhovsGun", "Film", "Casablanca", "The letters.")
        insert_relation(db_path, "Main", "ChekhovsGun", "Related", "Main", "RedHerring")
        insert_work_trope(db_path, "Film", "Casablanca", "Main", "ChekhovsGun")

        mark_extracted(db_path, page1["id"])
        stats = get_crawl_stats(db_path)
        assert stats["extracted"] == 1

        # Phase 4: Query via MCP query layer
        results = trope_search("dramatic", db_path=db_path)
        assert len(results) >= 1

        trope = trope_get("Main/ChekhovsGun", db_path=db_path)
        assert trope is not None
        assert trope["name"] == "Chekhov's Gun"
        assert len(trope["examples"]) == 1
        assert len(trope["related_tropes"]) == 1

        work = work_tropes("Film/Casablanca", db_path=db_path)
        assert len(work) == 1
