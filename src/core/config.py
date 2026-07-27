"""Application configuration loaded from environment variables.

All secrets and tunables are loaded from env vars (Rules.md §5).
Uses pydantic-settings for validation and type coercion.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings, loaded from environment variables.

    Env vars are prefixed with ``AVIOTHIC_`` (e.g., ``AVIOTHIC_API_KEY``).
    A ``.env`` file in the project root is loaded automatically in development.
    """

    model_config = SettingsConfigDict(
        env_prefix="AVIOTHIC_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Authentication ----------
    api_key: str = "change-me-to-a-real-key"

    # ---------- Upload ----------
    upload_max_bytes: int = 52_428_800  # 50 MB
    upload_dir: Path = Path("./uploads")
    allowed_mime_types: frozenset[str] = frozenset({"application/pdf"})

    # ---------- Logging ----------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ---------- Environment ----------
    env: Literal["development", "staging", "production"] = "development"

    # ---------- Application ----------
    app_name: str = "Aviothic Breast Cancer Report Copilot"
    app_version: str = "0.1.0"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
