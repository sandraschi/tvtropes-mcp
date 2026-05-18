"""Tests for scraper/db.py — SQLite schema, queue ops, structured data, FTS."""

from __future__ import annotations

import os
import tempfile

import pytest

from scraper.db import (
    count_crawled,
    count_extracted,
    count_pending,
    get_conn,
    get_crawl_stats,
    get_db_stats,
    get_related_tropes,
    get_trope,
    get_trope_examples,
    get_work_tropes,
    init_db,
    insert_example,
    insert_relation,
    insert_work_trope,
    list_namespaces,
    mark_crawled,
    mark_extracted,
    mark_failed,
    pop_pending,
    queue_urls,
    random_trope,
    search_tropes,
    upsert_trope,
)


@pytest.fixture
def db_path() -> str:
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "test.db")
    init_db(path)
    yield path
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


def test_init_db_creates_tables(db_path: str) -> None:
    with get_conn(db_path) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        names = [r["name"] for r in tables]
    assert "pages" in names
    assert "tropes" in names
    assert "examples" in names
    assert "trope_relations" in names
    assert "work_tropes" in names
    assert "tropes_fts" in names
    assert "crawl_log" in names


def test_queue_and_pop(db_path: str) -> None:
    urls = [
        {
            "url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsGun",
            "namespace": "Main",
            "page_name": "ChekhovsGun",
        },
        {
            "url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/Foreshadowing",
            "namespace": "Main",
            "page_name": "Foreshadowing",
        },
    ]
    added = queue_urls(db_path, urls)
    assert added == 2
    assert count_pending(db_path) == 2

    page = pop_pending(db_path)
    assert page is not None
    assert page["namespace"] == "Main"
    assert page["page_name"] in ("ChekhovsGun", "Foreshadowing")


def test_queue_duplicates(db_path: str) -> None:
    urls = [
        {"url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/Test", "namespace": "Main", "page_name": "Test"},
    ]
    added = queue_urls(db_path, urls)
    assert added >= 1
    added_again = queue_urls(db_path, urls)
    assert added_again == 0, f"duplicate insert should be ignored, got {added_again}"
    assert count_pending(db_path) == 1


def test_mark_crawled(db_path: str) -> None:
    queue_urls(
        db_path, [{"url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/Test", "namespace": "Main", "page_name": "Test"}]
    )
    page = pop_pending(db_path)
    assert page is not None

    mark_crawled(db_path, page["id"], "abc123", 200)
    assert count_crawled(db_path) == 1
    assert count_pending(db_path) == 0


def test_mark_failed(db_path: str) -> None:
    queue_urls(
        db_path, [{"url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/Test", "namespace": "Main", "page_name": "Test"}]
    )
    page = pop_pending(db_path)
    mark_failed(db_path, page["id"], 503)
    # Should become pending again with retry_count=1
    assert get_crawl_stats(db_path)["failed"] == 0
    assert get_crawl_stats(db_path)["pending"] == 1


def test_upsert_trope(db_path: str) -> None:
    trope_id = upsert_trope(
        db_path,
        "Main",
        "ChekhovsGun",
        title="Chekhov's Gun",
        description="A dramatic principle.",
        laconic="Every element must be necessary.",
    )
    assert trope_id > 0

    trope = get_trope(db_path, "Main/ChekhovsGun")
    assert trope is not None
    assert trope["title"] == "Chekhov's Gun"
    assert trope["description"] == "A dramatic principle."


def test_upsert_trope_duplicate(db_path: str) -> None:
    upsert_trope(db_path, "Main", "Test", title="Original")
    upsert_trope(db_path, "Main", "Test", title="Updated")
    trope = get_trope(db_path, "Main/Test")
    assert trope["title"] == "Updated"


def test_insert_examples(db_path: str) -> None:
    upsert_trope(db_path, "Main", "ChekhovsGun", title="Chekhov's Gun")
    insert_example(db_path, "Main", "ChekhovsGun", "Film", "Casablanca", "The letters of transit.")
    insert_example(db_path, "Main", "ChekhovsGun", "Series", "BreakingBad", "The pizza on the roof.")

    examples = get_trope_examples(db_path, "Main/ChekhovsGun")
    assert len(examples) == 2


def test_insert_examples_filtered(db_path: str) -> None:
    upsert_trope(db_path, "Main", "ChekhovsGun")
    insert_example(db_path, "Main", "ChekhovsGun", "Film", "Casablanca", "Text")
    insert_example(db_path, "Main", "ChekhovsGun", "Series", "BreakingBad", "Text")

    film_examples = get_trope_examples(db_path, "Main/ChekhovsGun", namespace="Film", limit=10)
    assert len(film_examples) == 1
    assert film_examples[0]["work_name"] == "Casablanca"


def test_work_tropes(db_path: str) -> None:
    upsert_trope(db_path, "Main", "ChekhovsGun")
    upsert_trope(db_path, "Main", "RedHerring")
    insert_work_trope(db_path, "Film", "Casablanca", "Main", "ChekhovsGun")
    insert_work_trope(db_path, "Film", "Casablanca", "Main", "RedHerring")

    tropes = get_work_tropes(db_path, "Film/Casablanca")
    assert len(tropes) == 2


def test_trope_relations(db_path: str) -> None:
    insert_relation(db_path, "Main", "AntiHero", "SubTrope", "Main", "ByronicHero")
    insert_relation(db_path, "Main", "AntiHero", "SuperTrope", "Main", "NominalHero")
    insert_relation(db_path, "Main", "AntiHero", "SisterTrope", "Main", "VillainProtagonist")

    related = get_related_tropes(db_path, "Main/AntiHero")
    assert len(related["sub_tropes"]) == 1
    assert len(related["super_tropes"]) == 1
    assert len(related["sister_tropes"]) == 1
    assert related["sub_tropes"][0]["page_name"] == "ByronicHero"


def test_list_namespaces(db_path: str) -> None:
    upsert_trope(db_path, "Main", "ChekhovsGun")
    upsert_trope(db_path, "Main", "RedHerring")
    upsert_trope(db_path, "Film", "Casablanca")

    namespaces = list_namespaces(db_path)
    assert len(namespaces) == 2
    ns_map = {n["namespace"]: n["page_count"] for n in namespaces}
    assert ns_map["Main"] == 2
    assert ns_map["Film"] == 1


def test_random_trope_empty(db_path: str) -> None:
    assert random_trope(db_path) is None


def test_random_trope(db_path: str) -> None:
    upsert_trope(db_path, "Main", "ChekhovsGun", title="Chekhov's Gun")
    trope = random_trope(db_path)
    assert trope is not None
    assert trope["page_name"] == "ChekhovsGun"


def test_fts_search(db_path: str) -> None:
    upsert_trope(
        db_path,
        "Main",
        "ChekhovsGun",
        title="Chekhov's Gun",
        description="A dramatic principle where early details become important later.",
    )
    upsert_trope(
        db_path,
        "Main",
        "RedHerring",
        title="Red Herring",
        description="A misleading clue designed to distract the audience.",
    )

    results = search_tropes(db_path, "dramatic", limit=10)
    assert len(results) >= 1
    assert any("ChekhovsGun" in r["page_name"] for r in results)

    results = search_tropes(db_path, "misleading", limit=10)
    assert len(results) >= 1
    assert any("RedHerring" in r["page_name"] for r in results)


def test_get_trope_not_found(db_path: str) -> None:
    assert get_trope(db_path, "Main/Nonexistent") is None


def test_get_crawl_stats_empty(db_path: str) -> None:
    stats = get_crawl_stats(db_path)
    assert stats["total"] == 0
    assert stats["pending"] == 0
    assert stats["crawled"] == 0


def test_get_db_stats_empty(db_path: str) -> None:
    stats = get_db_stats(db_path)
    assert stats["tropes"] == 0
    assert stats["examples"] == 0
    assert stats["size_mb"] > 0  # empty DB still has file size


def test_mark_extracted(db_path: str) -> None:
    queue_urls(
        db_path, [{"url": "https://tvtropes.org/pmwiki/pmwiki.php/Main/Test", "namespace": "Main", "page_name": "Test"}]
    )
    page = pop_pending(db_path)
    mark_crawled(db_path, page["id"], "hash123", 200)
    mark_extracted(db_path, page["id"])
    assert count_extracted(db_path) == 1
    assert get_crawl_stats(db_path)["extracted"] == 1
