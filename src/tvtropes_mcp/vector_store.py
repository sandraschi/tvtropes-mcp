"""LanceDB vector store for semantic trope search via Ollama embeddings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import lancedb

log = logging.getLogger(__name__)

DEFAULT_TABLE_NAME = "tropes"
EMBEDDING_DIM = 768  # nomic-embed-text


def _get_uri(data_dir: str | Path) -> str:
    return str(Path(data_dir) / "lancedb")


def open_db(data_dir: str | Path) -> lancedb.DBConnection:
    return lancedb.connect(_get_uri(data_dir))


def ensure_table(data_dir: str | Path) -> lancedb.table.Table:
    import pyarrow as pa

    db = open_db(data_dir)
    try:
        table = db.open_table(DEFAULT_TABLE_NAME)
        log.info(f"Opened existing LanceDB table '{DEFAULT_TABLE_NAME}'")
        return table
    except Exception:
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("namespace", pa.string()),
            pa.field("page_name", pa.string()),
            pa.field("title", pa.string()),
            pa.field("description", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
        ])
        table = db.create_table(DEFAULT_TABLE_NAME, schema=schema, mode="create")
        log.info(f"Created LanceDB table '{DEFAULT_TABLE_NAME}'")
        return table


async def get_embedding(
    text: str,
    ollama_host: str = "http://localhost:11434",
    model: str = "nomic-embed-text",
) -> list[float] | None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{ollama_host}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            if r.status_code == 200:
                return r.json().get("embedding")
            log.warning(f"Ollama embedding HTTP {r.status_code}")
            return None
    except Exception as e:
        log.debug(f"Ollama embedding unavailable: {e}")
        return None


def _make_text(trope: dict[str, Any]) -> str:
    parts = [trope.get("title") or trope.get("page_name", "")]
    desc = trope.get("description") or ""
    if desc:
        parts.append(desc)
    laconic = trope.get("laconic") or ""
    if laconic:
        parts.append(laconic)
    return "\n".join(parts)


async def upsert_trope_embedding(
    data_dir: str | Path,
    trope: dict[str, Any],
    ollama_host: str = "http://localhost:11434",
    model: str = "nomic-embed-text",
) -> bool:
    text = _make_text(trope)
    if not text.strip():
        return False
    embedding = await get_embedding(text, ollama_host, model)
    if embedding is None:
        return False
    table = ensure_table(data_dir)
    trope_id = f"{trope['namespace']}/{trope['page_name']}"
    record = {
        "id": trope_id,
        "namespace": trope["namespace"],
        "page_name": trope["page_name"],
        "title": trope.get("title") or trope.get("page_name", ""),
        "description": trope.get("description") or "",
        "text": text,
        "vector": embedding,
    }
    table.merge_insert(["id"]).when_matched_update_all().execute([record])
    return True


async def semantic_search(
    query: str,
    data_dir: str | Path,
    limit: int = 10,
    ollama_host: str = "http://localhost:11434",
    model: str = "nomic-embed-text",
) -> list[dict[str, Any]]:
    query_emb = await get_embedding(query, ollama_host, model)
    if query_emb is None:
        return [{"error": "Embedding unavailable — is Ollama running with nomic-embed-text?"}]
    try:
        table = open_db(data_dir).open_table(DEFAULT_TABLE_NAME)
        results = (
            table.search(query_emb)
            .limit(limit)
            .to_list()
        )
        return [
            {
                "id": r["id"],
                "namespace": r["namespace"],
                "page_name": r["page_name"],
                "title": r["title"],
                "description": r["description"][:300] if r.get("description") else "",
                "score": round(1.0 - float(r.get("_distance", 0)), 4),
            }
            for r in results
        ]
    except Exception as e:
        log.warning(f"Semantic search error: {e}")
        return [{"error": str(e)}]


def count_vectors(data_dir: str | Path) -> int:
    try:
        table = open_db(data_dir).open_table(DEFAULT_TABLE_NAME)
        return table.count_rows()
    except Exception:
        return 0
