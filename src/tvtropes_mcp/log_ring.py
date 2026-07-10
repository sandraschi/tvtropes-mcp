"""In-memory ring buffer + file-based rotating log. Accessible via REST API."""

from __future__ import annotations

import logging
import logging.handlers
import sys
import threading
import time
from pathlib import Path
from typing import Any


class LogRingHandler(logging.Handler):
    """A logging handler that keeps the last N records in a ring buffer."""

    def __init__(self, capacity: int = 2000) -> None:
        super().__init__()
        self.capacity = capacity
        self._lock = threading.Lock()
        self._buffer: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
            "level": record.levelname.lower(),
            "name": record.name,
            "message": record.getMessage(),
        }
        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) > self.capacity:
                self._buffer.pop(0)

    def get_recent(
        self,
        limit: int = 100,
        level: str | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self._lock:
            entries = list(self._buffer)
            if level:
                entries = [e for e in entries if e["level"] == level]
            return entries[-(limit + offset) : len(entries) - offset if offset else None][-limit:]


_ring = LogRingHandler()


def install_log_ring(data_dir: str | Path | None = None) -> None:
    """Install ring buffer handler, rotating file handler, and ERROR-only stderr.

    INFO/DEBUG goes to the log file only. ERROR also goes to stderr.
    """
    root = logging.getLogger()

    # Remove any existing stderr StreamHandlers (typically from basicConfig)
    for h in list(root.handlers):
        if isinstance(h, logging.StreamHandler) and h.stream in (sys.stderr, sys.stdout):
            root.removeHandler(h)

    root.addHandler(_ring)

    if data_dir is None:
        from tvtropes_mcp.config import load_settings
        data_dir = load_settings().resolved_data_dir()

    log_dir = Path(data_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "tvtropes.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(file_handler)

    # ERROR-only stderr handler — INFO/DEBUG stay out of the console
    err_handler = logging.StreamHandler(sys.stderr)
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(err_handler)


def get_recent(
    limit: int = 100,
    level: str | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return _ring.get_recent(limit=limit, level=level, offset=offset)


def export_json() -> list[dict[str, Any]]:
    return _ring.get_recent(limit=2000)
