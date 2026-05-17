"""CLI: stdio (Cursor), combined HTTP server (FastAPI + MCP), or standalone scraper."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

import uvicorn

from tvtropes_mcp.config import load_settings


def _configure_logging(*, debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="tvtropes-mcp (FastMCP 3.2)")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run FastAPI on TVTROPES_MCP_HOST:TVTROPES_MCP_PORT with MCP mounted at /mcp",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run MCP over stdio (default when --serve is not passed)",
    )
    parser.add_argument("--debug", action="store_true", help="Verbose logs (stderr only)")
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Run scraper daemon (crawler + extractor) standalone",
    )
    args = parser.parse_args()
    _configure_logging(debug=args.debug)

    transport = os.getenv("MCP_TRANSPORT", "").lower()
    use_http = args.serve or transport in {"http", "streamable"}

    if use_http and args.stdio:
        parser.error("Choose either --serve or --stdio, not both.")

    if args.scrape:
        _run_scraper(debug=args.debug)
        return

    from tvtropes_mcp.server import mcp

    settings = load_settings()

    if use_http:
        uvicorn.run(
            "tvtropes_mcp.app:app",
            host=settings.host,
            port=settings.port,
            log_level="debug" if args.debug else "info",
        )
        return

    asyncio.run(mcp.run_stdio_async())


def _run_scraper(*, debug: bool) -> None:
    import time

    from tvtropes_mcp.config import load_settings
    from tvtropes_mcp.db import ensure_db

    settings = load_settings()

    logging.getLogger("tvtropes_mcp").setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger("scraper").setLevel(logging.DEBUG if debug else logging.INFO)

    db_path = str(settings.resolved_data_dir() / "tvtropes.db")
    ensure_db(db_path)

    from scraper.db import get_crawl_stats, load_config
    from scraper.scheduler import CrawlScheduler

    config = load_config()
    scheduler = CrawlScheduler(db_path, config)
    scheduler.start()

    print(f"Scraper daemon started. DB: {db_path}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(60)
            stats = get_crawl_stats(db_path)
            print(
                f"  Crawl: {stats['extracted']} extracted, {stats['crawled']} crawled, "
                f"{stats['pending']} pending, {stats['failed']} failed, "
                f"{stats['blocked']} blocked, {stats['daily']} today"
            )
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        scheduler.stop()
        print("Done.")


if __name__ == "__main__":
    main()
