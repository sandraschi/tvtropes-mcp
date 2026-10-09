"""Runtime configuration for tvtropes-mcp."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Relative paths resolve against the repo root, never the CWD: Claude Desktop
# spawns stdio servers with cwd=C:\Windows\System32 (BUG-063).
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TVTROPES_MCP_",
        env_file=str(_REPO_ROOT / ".env"),
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 10964
    data_dir: Path | None = None
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:27b"
    ollama_timeout: float = 120.0
    api_mode: str = "ollama"
    openai_chat_model: str = "qwen/qwen3.6-27b"
    openai_embedding_model: str = "text-embedding-nomic-embed-text-v1.5"
    scraper_delay_min: float = 8.0
    scraper_delay_max: float = 15.0
    scraper_daily_budget: int = 7000
    openserp_url: str = "http://127.0.0.1:7000"

    def resolved_data_dir(self) -> Path:
        base = self.data_dir
        if base is None:
            base = _REPO_ROOT / "data"
        elif not base.is_absolute():
            base = _REPO_ROOT / base
        base.mkdir(parents=True, exist_ok=True)
        return base


def load_settings() -> Settings:
    return Settings()
