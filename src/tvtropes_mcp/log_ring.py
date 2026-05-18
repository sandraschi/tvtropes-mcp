"""In-memory ring buffer for log entries — accessible via REST API."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any


class LogRingHandler(logging.Handler):
    """A logging handler that keeps the last N records in a ring buffer."""

    def __init__(self, capacity: int = 500) -> None:
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

    def get_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._buffer[-limit:])


_ring = LogRingHandler()


def install_log_ring() -> None:
    root = logging.getLogger()
    root.addHandler(_ring)


def get_recent(limit: int = 100) -> list[dict[str, Any]]:
    return _ring.get_recent(limit=limit)
