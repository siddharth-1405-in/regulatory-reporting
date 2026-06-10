"""Application configuration (env-driven)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# repo root: .../Regulatory Reporting
REPO_ROOT = Path(__file__).resolve().parents[5]
REFERENCE_DIR = REPO_ROOT / "reference_artifacts"
CAR_TEMPLATE = REFERENCE_DIR / "SAMA_CAR_SA01_Template.xlsx"
OWNERSHIP_MATRIX = REFERENCE_DIR / "Regulatory_Data_Ownership_Matrix.xlsx"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL is the production target (user-managed). Override via env.
    database_url: str = "postgresql+psycopg://car:car@localhost:5432/car"

    # Anthropic Claude — optional. When unset, agents use deterministic fallback.
    anthropic_api_key: str | None = None
    claude_model_reasoning: str = "claude-opus-4-8"
    claude_model_narrative: str = "claude-haiku-4-5-20251001"

    cors_origins: list[str] = ["http://localhost:3000"]
    app_name: str = "Agentic CAR Reporting Platform"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
