"""Shared fixtures and configuration for the tvtropes-mcp test suite."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from scraper.db import (
    init_db,
    insert_example,
    insert_relation,
    insert_work_trope,
    upsert_trope,
)


@pytest.fixture(autouse=True)
def _reset_env() -> Generator[None, None, None]:
    keys = [k for k in os.environ if k.startswith("TVTROPES_MCP_")]
    saved = {k: os.environ[k] for k in keys}
    for k in keys:
        del os.environ[k]
    yield
    os.environ.update(saved)


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def db_path(temp_dir: str) -> str:
    path = os.path.join(temp_dir, "tvtropes.db")
    init_db(path)
    return path


def _seed_db(db_path: str) -> None:
    """Populate a test database with realistic seed data."""
    upsert_trope(
        db_path, "Main", "ChekhovsGun",
        title="Chekhov's Gun",
        description="A dramatic principle where an element introduced early becomes critically significant later.",
        laconic="Every element in a story must be necessary.",
    )
    upsert_trope(
        db_path, "Main", "RedHerring", title="Red Herring",
        description="A misleading clue designed to distract the audience.",
    )
    upsert_trope(
        db_path, "Main", "AntiHero", title="Anti-Hero",
        description="A protagonist who lacks conventional heroic qualities.",
    )
    upsert_trope(
        db_path, "Main", "FiveManBand", title="Five-Man Band",
        description="A team of five characters whose archetypes form a narrative unit.",
    )
    upsert_trope(
        db_path, "Main", "MacGuffin", title="MacGuffin",
        description="A plot device that drives the story but is ultimately unimportant.",
    )
    upsert_trope(
        db_path, "Main", "Foreshadowing", title="Foreshadowing",
        description="A hint of what is to come later.",
    )
    upsert_trope(
        db_path, "Film", "Casablanca", title="Casablanca",
        description="An American romantic drama film from 1942.",
    )
    upsert_trope(
        db_path, "Series", "BreakingBad", title="Breaking Bad",
        description="An American crime drama television series.",
    )

    insert_example(db_path, "Main", "ChekhovsGun", "Film", "Casablanca", "The letters of transit.")
    insert_example(db_path, "Main", "ChekhovsGun", "Series", "BreakingBad", "The meth lab equipment.")
    insert_example(db_path, "Main", "RedHerring", "Film", "Casablanca", "The MacGuffin letters.")

    insert_relation(db_path, "Main", "AntiHero", "SubTrope", "Main", "ByronicHero")
    insert_relation(db_path, "Main", "AntiHero", "SuperTrope", "Main", "NominalHero")
    insert_relation(db_path, "Main", "AntiHero", "SisterTrope", "Main", "VillainProtagonist")
    insert_relation(db_path, "Main", "AntiHero", "Related", "Main", "AntiVillain")

    insert_work_trope(db_path, "Film", "Casablanca", "Main", "ChekhovsGun")
    insert_work_trope(db_path, "Film", "Casablanca", "Main", "MacGuffin")
    insert_work_trope(db_path, "Series", "BreakingBad", "Main", "ChekhovsGun")


@pytest.fixture
def client(temp_dir: str, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """FastAPI TestClient whose app uses a test DB, seeded with trope data AFTER creation.

    1. Set env var so the app creates its DB in temp_dir/tvtropes.db
    2. Import the app fresh (clearing cached modules)
    3. Seed the app's DB with test data
    4. Yield the TestClient
    """
    app_db_path = os.path.join(temp_dir, "tvtropes.db")
    monkeypatch.setenv("TVTROPES_MCP_DATA_DIR", temp_dir)

    for mod in list(sys.modules.keys()):
        if mod.startswith("tvtropes_mcp") or mod.startswith("scraper"):
            del sys.modules[mod]

    from tvtropes_mcp.app import build_app

    app = build_app()
    _seed_db(app_db_path)
    yield TestClient(app)
