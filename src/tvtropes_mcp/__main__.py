"""CLI: stdio (Cursor), combined HTTP server (FastAPI + MCP), or standalone scraper."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

import uvicorn

from tvtropes_mcp.config import load_settings


def _configure_logging(*, debug: bool) -> None:
    """Set root logger level. install_log_ring() adds file + ERROR->stderr handlers."""
    level = logging.DEBUG if debug else logging.INFO
    logging.getLogger().setLevel(level)


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
            log_config=None,
        )
        return

    HTTP_PROXY_URL = os.getenv("TVTROPES_MCP_API_URL", "http://127.0.0.1:10964/mcp")
    try:
        import httpx

        r = httpx.post(
            HTTP_PROXY_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "probe", "version": "1"},
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
            timeout=0.5,
        )
        if r.status_code == 200:
            from fastmcp.server import create_proxy

            proxy = create_proxy(HTTP_PROXY_URL, name="tvtropes-mcp")
            proxy.run(transport="stdio")
            return
    except Exception:
        pass

    asyncio.run(mcp.run_stdio_async())


def _run_scraper(*, debug: bool) -> None:
    import asyncio
    import time

    from tvtropes_mcp.config import load_settings
    from tvtropes_mcp.db import ensure_db

    settings = load_settings()

    log = logging.getLogger("tvtropes_mcp")
    log.setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger("scraper").setLevel(logging.DEBUG if debug else logging.INFO)

    db_path = str(settings.resolved_data_dir() / "tvtropes.db")
    ensure_db(db_path)

    from scraper.db import get_crawl_stats, load_config
    from scraper.extractor import Extractor
    from scraper.scheduler import CrawlScheduler

    config = load_config()
    scheduler = CrawlScheduler(db_path, config)
    scheduler.start()

    log.info(f"Scraper daemon started. DB: {db_path}")
    log.info("Press Ctrl+C to stop.")

    _extract_interval = 0

    try:
        while True:
            time.sleep(60)
            stats = get_crawl_stats(db_path)
            log.info(
                "Crawl: %d extracted, %d crawled, %d pending, %d failed, %d blocked, %d today",
                stats["extracted"],
                stats["crawled"],
                stats["pending"],
                stats["failed"],
                stats["blocked"],
                stats["daily"],
            )
            _extract_interval += 1
            if _extract_interval >= 5 and stats.get("crawled", 0) > 0:
                _extract_interval = 0
                logging.getLogger("scraper").info("Running extraction pass...")
                try:
                    extractor = Extractor(db_path, config)
                    try:
                        result = asyncio.run(extractor.run_pass(batch_size=5))
                        if result:
                            logging.getLogger("scraper").info(f"Extraction pass: {result.get('extracted', 0)} pages")
                    finally:
                        asyncio.run(extractor.close())
                except Exception as exc:
                    logging.getLogger("scraper").error(f"Extraction pass failed: {exc}", exc_info=True)
    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        scheduler.stop()
        log.info("Done.")


if __name__ == "__main__":
    main()
