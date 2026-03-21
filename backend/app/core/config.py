from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Cursor for 2D Animation API"
    environment: Literal["local", "staging", "production", "test"] = "local"
    debug: bool = False

    database_url: str = "sqlite:///./cursor2d.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Ollama (local LLM — set llm_provider="ollama" to use)
    llm_provider: str = "groq"  # "groq" or "ollama"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen3.5:9b"

    artifacts_dir: Path = Field(default=Path("./artifacts"))
    simulate_render: bool = True
    max_scene_duration_sec: int = 60

    # S3-compatible object storage (optional — leave blank to use local disk)
    s3_bucket: str = ""
    s3_endpoint_url: str = ""  # set for MinIO / Cloudflare R2 / etc.
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://localhost:3004",
            "http://localhost:3005",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:3003",
            "http://127.0.0.1:3004",
            "http://127.0.0.1:3005",
            "http://localhost",
            "http://127.0.0.1",
        ]
    )
    # Extra origins appended at runtime — comma-separated, set via EXTRA_CORS_ORIGINS env var.
    # Use this to add your production frontend URL without changing default list.
    # e.g. EXTRA_CORS_ORIGINS=https://animbolt-web.onrender.com,https://yourdomain.com
    extra_cors_origins: str = ""

    _WEAK_JWT_SECRETS = {"change-me", "change-me-in-prod", "secret", ""}

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):  # type: ignore[no-untyped-def]
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "debug"}
        return bool(value)

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:  # type: ignore[no-untyped-def]
        env = (info.data or {}).get("environment", "local")
        if env == "production" and v in Settings._WEAK_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a strong random secret in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v

    @field_validator("groq_api_key", mode="after")
    @classmethod
    def validate_groq_key(cls, v: str, info) -> str:  # type: ignore[no-untyped-def]
        env = (info.data or {}).get("environment", "local")
        if env == "production" and not v:
            import logging
            logging.getLogger(__name__).warning(
                "GROQ_API_KEY is not set — LLM generation will use fallback code only."
            )
        return v


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return settings
