"""Persistent user settings - stored in data/settings.json, overrides env vars."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from tvtropes_mcp.config import load_settings as _load_env

log = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"

DEFAULTS: dict[str, Any] = {
    "ollama_host": "http://localhost:11434",
    "ollama_model": "qwen2.5:27b",
    "ollama_timeout": 120.0,
    "api_mode": "ollama",
    "openai_chat_model": "qwen/qwen3.6-27b",
    "openai_embedding_model": "text-embedding-nomic-embed-text-v1.5",
    "scraper_delay_min": 8.0,
    "scraper_delay_max": 15.0,
    "scraper_daily_budget": 7000,
    "scraping_api_enabled": False,
    "scraping_api_provider": "scrapieapi",
    "scraping_api_key": "",
}


def _settings_path() -> Path:
    """Resolve settings.json path relative to the data directory."""
    env = _load_env()
    return env.resolved_data_dir() / SETTINGS_FILE


def _read() -> dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        return dict(DEFAULTS)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Failed to read settings: {e}")
        return dict(DEFAULTS)


def _write(data: dict[str, Any]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_all() -> dict[str, Any]:
    """Return merged settings: file overrides, env defaults as fallback."""
    env = _load_env()
    file_settings = _read()
    merged = {
        "ollama_host": file_settings.get("ollama_host", env.ollama_host),
        "ollama_model": file_settings.get("ollama_model", env.ollama_model),
        "ollama_timeout": file_settings.get("ollama_timeout", env.ollama_timeout),
        "api_mode": file_settings.get("api_mode", env.api_mode),
        "openai_chat_model": file_settings.get("openai_chat_model", env.openai_chat_model),
        "openai_embedding_model": file_settings.get("openai_embedding_model", env.openai_embedding_model),
        "scraper_delay_min": file_settings.get("scraper_delay_min", env.scraper_delay_min),
        "scraper_delay_max": file_settings.get("scraper_delay_max", env.scraper_delay_max),
        "scraper_daily_budget": file_settings.get("scraper_daily_budget", env.scraper_daily_budget),
        "scraping_api_enabled": file_settings.get("scraping_api_enabled", False),
        "scraping_api_provider": file_settings.get("scraping_api_provider", "scrapieapi"),
        "scraping_api_key": file_settings.get("scraping_api_key", ""),
        "data_dir": str(env.resolved_data_dir()),
        "host": env.host,
        "port": env.port,
    }
    return merged


def update(overrides: dict[str, Any]) -> dict[str, Any]:
    """Update specific settings keys and persist."""
    current = _read()
    allowed = {
        "ollama_host",
        "ollama_model",
        "ollama_timeout",
        "api_mode",
        "openai_chat_model",
        "openai_embedding_model",
        "scraper_delay_min",
        "scraper_delay_max",
        "scraper_daily_budget",
        "scraping_api_enabled",
        "scraping_api_provider",
        "scraping_api_key",
    }
    changed = []
    for key in allowed:
        if key in overrides and overrides[key] is not None:
            try:
                val = overrides[key]
                if isinstance(val, str) and val.strip():
                    current[key] = val.strip()
                    changed.append(key)
                elif isinstance(val, bool):
                    current[key] = val
                    changed.append(key)
                elif isinstance(val, (int, float)):
                    current[key] = float(val)
                    changed.append(key)
            except (ValueError, TypeError):
                pass
    if changed:
        _write(current)
        log.info(f"Settings updated: {', '.join(changed)}")
    return get_all()
