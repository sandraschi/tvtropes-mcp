"""SQLite schema, queue management, structured data storage, FTS5 search."""

from __future__ import annotations

import contextlib
import sqlite3
import time
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS pages (
    id          INTEGER PRIMARY KEY,
    url         TEXT UNIQUE NOT NULL,
    namespace   TEXT,
    page_name   TEXT,
    status      TEXT DEFAULT 'pending',  -- pending|crawled|failed|skipped|extracted
    crawled_at  TEXT,
    retry_count INTEGER DEFAULT 0,
    http_status INTEGER,
    blocked     BOOLEAN DEFAULT 0,
    content_hash TEXT
);

CREATE TABLE IF NOT EXISTS tropes (
    id          INTEGER PRIMARY KEY,
    namespace   TEXT NOT NULL,
    page_name   TEXT NOT NULL,
    title       TEXT,
    description TEXT,
    laconic     TEXT,
    image_url   TEXT,
    extracted_at TEXT,
    UNIQUE(namespace, page_name)
);

CREATE TABLE IF NOT EXISTS examples (
    id          INTEGER PRIMARY KEY,
    trope_ns    TEXT NOT NULL,
    trope_name  TEXT NOT NULL,
    work_ns     TEXT,
    work_name   TEXT,
    example_text TEXT,
    FOREIGN KEY(trope_ns, trope_name) REFERENCES tropes(namespace, page_name)
);

CREATE TABLE IF NOT EXISTS trope_relations (
    id          INTEGER PRIMARY KEY,
    from_ns     TEXT NOT NULL,
    from_name   TEXT NOT NULL,
    relation    TEXT NOT NULL,  -- SubTrope|SuperTrope|SisterTrope|Related
    to_ns       TEXT NOT NULL,
    to_name     TEXT NOT NULL,
    UNIQUE(from_ns, from_name, relation, to_ns, to_name)
);

CREATE TABLE IF NOT EXISTS work_tropes (
    id          INTEGER PRIMARY KEY,
    work_ns     TEXT NOT NULL,
    work_name   TEXT NOT NULL,
    trope_ns    TEXT NOT NULL,
    trope_name  TEXT NOT NULL,
    UNIQUE(work_ns, work_name, trope_ns, trope_name)
);

CREATE VIRTUAL TABLE IF NOT EXISTS tropes_fts USING fts5(
    page_name, title, description, laconic,
    tokenize='porter unicode61'
);

CREATE TABLE IF NOT EXISTS crawl_log (
    id           INTEGER PRIMARY KEY,
    session_id   TEXT,
    started_at   TEXT,
    ended_at     TEXT,
    pages_crawled INTEGER DEFAULT 0,
    pages_blocked INTEGER DEFAULT 0,
    errors       INTEGER DEFAULT 0
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status);
CREATE INDEX IF NOT EXISTS idx_pages_namespace ON pages(namespace);
CREATE INDEX IF NOT EXISTS idx_tropes_ns_name ON tropes(namespace, page_name);
CREATE INDEX IF NOT EXISTS idx_examples_trope ON examples(trope_ns, trope_name);
CREATE INDEX IF NOT EXISTS idx_examples_work ON examples(work_ns, work_name);
CREATE INDEX IF NOT EXISTS idx_trope_relations_from ON trope_relations(from_ns, from_name);
CREATE INDEX IF NOT EXISTS idx_trope_relations_to ON trope_relations(to_ns, to_name);
CREATE INDEX IF NOT EXISTS idx_work_tropes_work ON work_tropes(work_ns, work_name);
CREATE INDEX IF NOT EXISTS idx_work_tropes_trope ON work_tropes(trope_ns, trope_name);
"""


@dataclass
class Config:
    min_delay_s: float = 8.0
    max_delay_s: float = 15.0
    max_retries: int = 5
    backoff_base_minutes: int = 30
    backoff_max_hours: int = 4
    daily_budget: int = 7000
    session_rotate_every: int = 500
    accept_language: str = "de-AT,de;q=0.9,en;q=0.8,ja;q=0.7"
    accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    accept_encoding: str = "gzip, deflate, br"
    priority_namespaces: tuple[str, ...] = (
        "Main",
        "Laconic",
        "Film",
        "Series",
        "Anime",
        "Literature",
        "VideoGame",
        "WesternAnimation",
        "Music",
        "ComicBook",
        "Webcomic",
        "WebOriginal",
        "YMMV",
    )
    skip_namespaces: tuple[str, ...] = ("SandBox", "Administrivia", "Ptitle")
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:27b"
    ollama_timeout_s: float = 120.0
    ollama_concurrent: int = 2
    cache_dir: str = "scraper/cache"
    compress: bool = True
    db_path: str = "data/tvtropes.db"


def load_config(config_path: str | Path = "scraper/config.yaml") -> Config:
    path = Path(config_path)
    if not path.exists():
        return Config()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    c = raw.get("crawl", {})
    h = raw.get("headers", {})
    n = raw.get("namespaces", {})
    o = raw.get("ollama", {})
    s = raw.get("storage", {})
    return Config(
        min_delay_s=c.get("min_delay_s", 8.0),
        max_delay_s=c.get("max_delay_s", 15.0),
        max_retries=c.get("max_retries", 5),
        backoff_base_minutes=c.get("backoff_base_minutes", 30),
        backoff_max_hours=c.get("backoff_max_hours", 4),
        daily_budget=c.get("daily_budget", 7000),
        session_rotate_every=c.get("session_rotate_every", 500),
        accept_language=h.get("accept_language", "de-AT,de;q=0.9,en;q=0.8,ja;q=0.7"),
        accept=h.get("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        accept_encoding=h.get("accept_encoding", "gzip, deflate, br"),
        priority_namespaces=tuple(n.get("priority", Config.priority_namespaces)),
        skip_namespaces=tuple(n.get("skip", Config.skip_namespaces)),
        ollama_url=o.get("url", "http://localhost:11434"),
        ollama_model=o.get("model", "qwen2.5:27b"),
        ollama_timeout_s=o.get("timeout_s", 120.0),
        ollama_concurrent=o.get("concurrent", 2),
        db_path=s.get("db_path", "data/tvtropes.db"),
        cache_dir=s.get("cache_dir", "scraper/cache"),
        compress=s.get("compress", True),
    )


def resolve_db_path(data_dir: str | Path | None = None, config: Config | None = None) -> Path:
    if config is not None:
        return Path(config.db_path)
    if data_dir is not None:
        return Path(data_dir) / "tvtropes.db"
    return Path("data") / "tvtropes.db"


@contextlib.contextmanager
def get_conn(db_path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str | Path) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


# ─── Queue Operations ──────────────────────────────────────────────


def count_pending(db_path: str | Path) -> int:
    with get_conn(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM pages WHERE status='pending'").fetchone()[0]


def count_crawled(db_path: str | Path) -> int:
    with get_conn(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM pages WHERE status='crawled'").fetchone()[0]


def count_extracted(db_path: str | Path) -> int:
    with get_conn(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM pages WHERE status='extracted'").fetchone()[0]


def count_failed(db_path: str | Path) -> int:
    with get_conn(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM pages WHERE status='failed'").fetchone()[0]


def pop_pending(db_path: str | Path) -> dict[str, Any] | None:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT id, url, namespace, page_name, retry_count FROM pages "
            "WHERE status='pending' ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE pages SET status='crawling' WHERE id=?", (row["id"],))
        conn.commit()
        return dict(row)


def mark_crawled(
    db_path: str | Path,
    page_id: int,
    content_hash: str,
    http_status: int,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "UPDATE pages SET status='crawled', crawled_at=datetime('now'), "
            "content_hash=?, http_status=?, retry_count=0, blocked=0 WHERE id=?",
            (content_hash, http_status, page_id),
        )
        conn.commit()


def mark_failed(db_path: str | Path, page_id: int, http_status: int | None = None) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "UPDATE pages SET retry_count=retry_count+1, http_status=?, "
            "status=CASE WHEN retry_count>=5 THEN 'skipped' ELSE 'pending' END "
            "WHERE id=?",
            (http_status, page_id),
        )
        conn.commit()


def mark_blocked(db_path: str | Path, page_id: int) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "UPDATE pages SET status='pending', blocked=1, retry_count=retry_count+1 WHERE id=?",
            (page_id,),
        )
        conn.commit()


def mark_extracted(db_path: str | Path, page_id: int) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "UPDATE pages SET status='extracted' WHERE id=?",
            (page_id,),
        )
        conn.commit()


def queue_urls(db_path: str | Path, urls: list[dict[str, str]]) -> int:
    with get_conn(db_path) as conn:
        before = conn.total_changes
        for u in urls:
            conn.execute(
                "INSERT OR IGNORE INTO pages(url, namespace, page_name) VALUES (?, ?, ?)",
                (u["url"], u.get("namespace"), u.get("page_name")),
            )
        conn.commit()
        return conn.total_changes - before


def get_namespace_counts(db_path: str | Path) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT namespace, COUNT(*) as page_count FROM pages "
            "WHERE namespace IS NOT NULL AND namespace != '' "
            "GROUP BY namespace ORDER BY page_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_crawl_stats(db_path: str | Path) -> dict[str, Any]:
    with get_conn(db_path) as conn:
        pending = conn.execute("SELECT COUNT(*) FROM pages WHERE status='pending'").fetchone()[0]
        crawling = conn.execute("SELECT COUNT(*) FROM pages WHERE status='crawling'").fetchone()[0]
        crawled = conn.execute("SELECT COUNT(*) FROM pages WHERE status='crawled'").fetchone()[0]
        extracted = conn.execute("SELECT COUNT(*) FROM pages WHERE status='extracted'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM pages WHERE status='failed'").fetchone()[0]
        skipped = conn.execute("SELECT COUNT(*) FROM pages WHERE status='skipped'").fetchone()[0]
        blocked = conn.execute("SELECT COUNT(*) FROM pages WHERE blocked=1").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        daily = conn.execute(
            "SELECT COUNT(*) FROM pages WHERE status IN ('crawled','extracted') AND date(crawled_at)=date('now')"
        ).fetchone()[0]
        return {
            "total": total,
            "pending": pending,
            "crawling": crawling,
            "crawled": crawled,
            "extracted": extracted,
            "failed": failed,
            "skipped": skipped,
            "blocked": blocked,
            "daily": daily,
        }


# ─── Structured Data Queries ───────────────────────────────────────


def search_tropes(
    db_path: str | Path,
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        fts_sql = (
            "SELECT t.id, t.namespace, t.page_name, t.title, t.description, "
            "  t.laconic, rank "
            "FROM tropes_fts "
            "JOIN tropes t ON t.id = tropes_fts.rowid "
            "WHERE tropes_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ?"
        )
        rows = conn.execute(fts_sql, (query, limit)).fetchall()
        return [dict(r) for r in rows]


def get_trope(db_path: str | Path, trope_id: str) -> dict[str, Any] | None:
    ns, name = _split_trope_id(trope_id)
    with get_conn(db_path) as conn:
        trope = conn.execute(
            "SELECT * FROM tropes WHERE namespace=? AND page_name=?",
            (ns, name),
        ).fetchone()
        if trope is None:
            return None
        result = dict(trope)
        examples = conn.execute(
            "SELECT work_ns, work_name, example_text FROM examples WHERE trope_ns=? AND trope_name=? LIMIT 100",
            (ns, name),
        ).fetchall()
        result["examples"] = [dict(e) for e in examples]
        sub = conn.execute(
            "SELECT to_ns, to_name FROM trope_relations WHERE from_ns=? AND from_name=? AND relation='SubTrope'",
            (ns, name),
        ).fetchall()
        super_ = conn.execute(
            "SELECT to_ns, to_name FROM trope_relations WHERE from_ns=? AND from_name=? AND relation='SuperTrope'",
            (ns, name),
        ).fetchall()
        sister = conn.execute(
            "SELECT to_ns, to_name FROM trope_relations WHERE from_ns=? AND from_name=? AND relation='SisterTrope'",
            (ns, name),
        ).fetchall()
        related = conn.execute(
            "SELECT to_ns, to_name FROM trope_relations WHERE from_ns=? AND from_name=? AND relation='Related'",
            (ns, name),
        ).fetchall()
        result["sub_tropes"] = [{"namespace": r["to_ns"], "page_name": r["to_name"]} for r in sub]
        result["super_tropes"] = [{"namespace": r["to_ns"], "page_name": r["to_name"]} for r in super_]
        result["sister_tropes"] = [{"namespace": r["to_ns"], "page_name": r["to_name"]} for r in sister]
        result["related_tropes"] = [{"namespace": r["to_ns"], "page_name": r["to_name"]} for r in related]
        return result


def get_work_tropes(db_path: str | Path, work_id: str) -> list[dict[str, Any]]:
    ns, name = _split_trope_id(work_id)
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT wt.trope_ns, wt.trope_name, t.title, t.description "
            "FROM work_tropes wt "
            "LEFT JOIN tropes t ON t.namespace=wt.trope_ns AND t.page_name=wt.trope_name "
            "WHERE wt.work_ns=? AND wt.work_name=? "
            "ORDER BY wt.trope_ns, wt.trope_name",
            (ns, name),
        ).fetchall()
        return [dict(r) for r in rows]


def get_trope_examples(
    db_path: str | Path,
    trope_id: str,
    namespace: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    ns, name = _split_trope_id(trope_id)
    with get_conn(db_path) as conn:
        if namespace:
            rows = conn.execute(
                "SELECT work_ns, work_name, example_text FROM examples "
                "WHERE trope_ns=? AND trope_name=? AND work_ns=? "
                "LIMIT ?",
                (ns, name, namespace, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT work_ns, work_name, example_text FROM examples WHERE trope_ns=? AND trope_name=? LIMIT ?",
                (ns, name, limit),
            ).fetchall()
        return [dict(r) for r in rows]


def get_related_tropes(
    db_path: str | Path,
    trope_id: str,
) -> dict[str, list[dict[str, str]]]:
    ns, name = _split_trope_id(trope_id)
    with get_conn(db_path) as conn:
        sub = conn.execute(
            "SELECT to_ns, to_name FROM trope_relations WHERE from_ns=? AND from_name=? AND relation='SubTrope'",
            (ns, name),
        ).fetchall()
        super_ = conn.execute(
            "SELECT to_ns, to_name FROM trope_relations WHERE from_ns=? AND from_name=? AND relation='SuperTrope'",
            (ns, name),
        ).fetchall()
        sister = conn.execute(
            "SELECT to_ns, to_name FROM trope_relations WHERE from_ns=? AND from_name=? AND relation='SisterTrope'",
            (ns, name),
        ).fetchall()
        related = conn.execute(
            "SELECT to_ns, to_name FROM trope_relations WHERE from_ns=? AND from_name=? AND relation='Related'",
            (ns, name),
        ).fetchall()
        return {
            "sub_tropes": [{"namespace": r["to_ns"], "page_name": r["to_name"]} for r in sub],
            "super_tropes": [{"namespace": r["to_ns"], "page_name": r["to_name"]} for r in super_],
            "sister_tropes": [{"namespace": r["to_ns"], "page_name": r["to_name"]} for r in sister],
            "related_tropes": [{"namespace": r["to_ns"], "page_name": r["to_name"]} for r in related],
        }


def list_namespaces(db_path: str | Path) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT namespace, COUNT(*) as page_count FROM tropes GROUP BY namespace ORDER BY page_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def random_trope(db_path: str | Path) -> dict[str, Any] | None:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT t.*, "
            "  (SELECT COUNT(*) FROM examples e "
            "   WHERE e.trope_ns=t.namespace AND e.trope_name=t.page_name) as example_count "
            "FROM tropes t "
            "ORDER BY RANDOM() "
            "LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return dict(row)


def get_db_stats(db_path: str | Path) -> dict[str, Any]:
    with get_conn(db_path) as conn:
        tropes_count = conn.execute("SELECT COUNT(*) FROM tropes").fetchone()[0]
        examples_count = conn.execute("SELECT COUNT(*) FROM examples").fetchone()[0]
        relations_count = conn.execute("SELECT COUNT(*) FROM trope_relations").fetchone()[0]
        work_tropes_count = conn.execute("SELECT COUNT(*) FROM work_tropes").fetchone()[0]
        db_size = Path(db_path).stat().st_size if Path(db_path).exists() else 0
        return {
            "size_mb": round(db_size / (1024 * 1024), 2),
            "tropes": tropes_count,
            "examples": examples_count,
            "trope_relations": relations_count,
            "work_tropes": work_tropes_count,
        }


# ─── Data Ingestion (used by extractor.py) ─────────────────────────


def upsert_trope(
    db_path: str | Path,
    namespace: str,
    page_name: str,
    title: str | None = None,
    description: str | None = None,
    laconic: str | None = None,
    image_url: str | None = None,
) -> int:
    with get_conn(db_path) as conn:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO tropes(namespace, page_name, title, description, laconic, image_url, extracted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(namespace, page_name) DO UPDATE SET "
            "title=COALESCE(excluded.title, title), "
            "description=COALESCE(excluded.description, description), "
            "laconic=COALESCE(excluded.laconic, laconic), "
            "image_url=COALESCE(excluded.image_url, image_url), "
            "extracted_at=excluded.extracted_at",
            (namespace, page_name, title, description, laconic, image_url, now),
        )
        trope_id = conn.execute(
            "SELECT id FROM tropes WHERE namespace=? AND page_name=?",
            (namespace, page_name),
        ).fetchone()[0]
        _sync_fts(conn, trope_id, page_name, title, description, laconic)
        conn.commit()
        return trope_id


def _sync_fts(
    conn: sqlite3.Connection,
    trope_id: int,
    page_name: str,
    title: str | None,
    description: str | None,
    laconic: str | None,
) -> None:
    conn.execute("DELETE FROM tropes_fts WHERE rowid=?", (trope_id,))
    conn.execute(
        "INSERT INTO tropes_fts(rowid, page_name, title, description, laconic) VALUES (?, ?, ?, ?, ?)",
        (trope_id, page_name, title or "", description or "", laconic or ""),
    )


def insert_example(
    db_path: str | Path,
    trope_ns: str,
    trope_name: str,
    work_ns: str | None = None,
    work_name: str | None = None,
    example_text: str | None = None,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO examples(trope_ns, trope_name, work_ns, work_name, example_text) VALUES (?, ?, ?, ?, ?)",
            (trope_ns, trope_name, work_ns, work_name, example_text),
        )
        conn.commit()


def insert_relation(
    db_path: str | Path,
    from_ns: str,
    from_name: str,
    relation: str,
    to_ns: str,
    to_name: str,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO trope_relations(from_ns, from_name, relation, to_ns, to_name) "
            "VALUES (?, ?, ?, ?, ?)",
            (from_ns, from_name, relation, to_ns, to_name),
        )
        conn.commit()


def insert_work_trope(
    db_path: str | Path,
    work_ns: str,
    work_name: str,
    trope_ns: str,
    trope_name: str,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO work_tropes(work_ns, work_name, trope_ns, trope_name) VALUES (?, ?, ?, ?)",
            (work_ns, work_name, trope_ns, trope_name),
        )
        conn.commit()


# ─── Crawl Log ─────────────────────────────────────────────────────


def start_crawl_session(db_path: str | Path, session_id: str) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO crawl_log(session_id, started_at) VALUES (?, datetime('now'))",
            (session_id,),
        )
        conn.commit()


def end_crawl_session(
    db_path: str | Path,
    session_id: str,
    pages_crawled: int,
    pages_blocked: int,
    errors: int,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            "UPDATE crawl_log SET ended_at=datetime('now'), "
            "pages_crawled=?, pages_blocked=?, errors=? WHERE session_id=?",
            (pages_crawled, pages_blocked, errors, session_id),
        )
        conn.commit()


def get_recent_crawl_sessions(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM crawl_log ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Helpers ───────────────────────────────────────────────────────


def _split_trope_id(trope_id: str) -> tuple[str, str]:
    parts = trope_id.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "Main", parts[0]


# ─── Exported for MCP query layer ──────────────────────────────────


def format_trope_name(namespace: str, page_name: str) -> str:
    return f"{namespace}/{page_name}"
