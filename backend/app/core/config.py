from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "ScholarSync"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "dev-only-insecure-secret-change-in-production-32chars"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/scholarsync"

    frontend_origin: str = "http://localhost:5173"
    trusted_hosts: str = "localhost,127.0.0.1"

    # Session cookies
    session_cookie_name: str = "scholarsync_session"
    session_ttl_hours: int = 168  # 7 days

    # Gemini AI (optional)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    # Collectors, active web discovery & monitoring
    sync_on_startup: bool = False
    allow_live_web_discovery: bool = True
    collector_user_agent: str = "ScholarSync-OfficialSourceVerifier/1.0"
    collector_timeout_seconds: int = 15
    web_discovery_timeout_seconds: int = 8
    stale_after_days: int = 14

    # Optional initial admin bootstrap (no hardcoded password defaults)
    admin_email: str = ""
    admin_initial_password: str = ""
    admin_full_name: str = "ScholarSync Admin"

    # Rate limiting (requests per window)
    auth_rate_limit_per_minute: int = 20
    assistant_rate_limit_per_minute: int = 25

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if cleaned.startswith("postgres://"):
            return "postgresql+psycopg://" + cleaned[len("postgres://") :]
        if cleaned.startswith("postgresql://") and "+psycopg" not in cleaned:
            return "postgresql+psycopg://" + cleaned[len("postgresql://") :]
        return cleaned

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        if self.app_env == "production":
            if (
                not self.secret_key
                or "dev-only" in self.secret_key
                or "replace-with" in self.secret_key
                or len(self.secret_key) < 32
            ):
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and non-default in production."
                )
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
