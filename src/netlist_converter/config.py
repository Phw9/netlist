"""Application configuration via environment variables."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class LLMProviderType(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class OutputFormat(str, Enum):
    SPICE = "spice"
    EDIF = "edif"
    KICAD = "kicad"
    JSON = "json"


class Settings(BaseSettings):
    """Central configuration loaded from .env or environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    llm_provider: LLMProviderType = LLMProviderType.OLLAMA

    ollama_base_url: str = "http://localhost:11434"
    ollama_vision_model: str = "llama3.2-vision"
    ollama_embed_model: str = "nomic-embed-text"

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    sqlite_db_path: Path = Field(default=PROJECT_ROOT / "data" / "db" / "netlist.db")
    chroma_db_path: Path = Field(default=PROJECT_ROOT / "data" / "db" / "chroma")

    upload_dir: Path = Field(default=PROJECT_ROOT / "data" / "uploads")
    output_dir: Path = Field(default=PROJECT_ROOT / "data" / "outputs")

    web_host: str = "0.0.0.0"
    web_port: int = 8000

    default_output_format: OutputFormat = OutputFormat.SPICE

    def ensure_directories(self) -> None:
        """Create required directories if they do not exist."""
        for directory in (self.upload_dir, self.output_dir, self.sqlite_db_path.parent, self.chroma_db_path):
            directory.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
