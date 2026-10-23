from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    ENVIRONMENT: str = Field(
        default="development", description="Runtime environment: development, testing, production"
    )
    PROJECT_NAME: str = Field(default="Sahaayak AI", description="System project title")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API route prefix")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./sahaayak.db",
        description="Database connection URL (PostgreSQL or SQLite fallback)",
    )

    # JWT / Security Secret
    SECRET_KEY: str = Field(
        default="sahaayak_super_secret_jwt_key_minimum_32_characters_long",
        description="JWT cryptographic signing secret",
    )

    # CORS Allowlist
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origin domains",
    )

    # AI Configuration (Google Gemini)
    AI_MODE: Literal["demo", "gemini"] = Field(
        default="demo",
        description="AI engine mode: demo (deterministic mock) or gemini (live Google Gemini API)",
    )
    GEMINI_API_KEY: Optional[str] = Field(
        default=None, description="Google Gemini API key required when AI_MODE=gemini"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash", description="Target Google Gemini model ID"
    )

    # Upload & Retention Policy
    MAX_UPLOAD_MB: int = Field(
        default=10, ge=1, le=50, description="Max upload file size in megabytes"
    )
    RETENTION_DAYS: int = Field(
        default=30, ge=1, description="Audit and media retention period in days"
    )
    UPLOAD_DIR: str = Field(default="./uploads", description="Local file upload directory")
    ALLOWED_IMAGE_TYPES: List[str] = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        description="Allowed MIME types for field images",
    )

    @property
    def MAX_UPLOAD_SIZE_MB(self) -> int:
        return self.MAX_UPLOAD_MB

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, ge=1, description="Global rate limit requests per minute per IP"
    )
    RATE_LIMIT_BURST: int = Field(default=20, ge=1, description="Rate limit burst allowance")

    # Live Official Sources Settings (e.g. NDMA SACHET & IMD)
    LIVE_SOURCES_ENABLED: bool = Field(
        default=False, description="Enable background ingestion of external live feeds"
    )
    SACHET_FEED_URLS: List[str] = Field(
        default=["https://sachet.ndma.gov.in/feed/cap_rss"],
        description="NDMA SACHET CAP alert RSS/Atom feed URLs",
    )
    IMD_API_BASE_URL: str = Field(
        default="https://api.imd.gov.in/v1",
        description="India Meteorological Department API base URL",
    )
    IMD_API_KEY: Optional[str] = Field(default=None, description="IMD API Access Key")
    LIVE_REFRESH_MINUTES: int = Field(
        default=15, ge=1, description="Polling interval for live feeds in minutes"
    )
    LIVE_HTTP_TIMEOUT_SECONDS: float = Field(
        default=10.0, ge=1.0, description="HTTP client timeout for live sources"
    )
    LIVE_MAX_PAYLOAD_KB: int = Field(
        default=512, ge=16, description="Max live source payload size in KB to prevent SSRF/DOS"
    )
    LIVE_DATA_FALLBACK: Literal["off", "labelled_demo"] = Field(
        default="off", description="Live data fallback policy: 'off' or 'labelled_demo'"
    )

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: Optional[str], info) -> Optional[str]:
        # If AI_MODE is explicitly 'gemini', GEMINI_API_KEY must not be empty
        mode = info.data.get("AI_MODE")
        if mode == "gemini" and (not v or not v.strip()):
            raise ValueError("GEMINI_API_KEY is required and cannot be empty when AI_MODE='gemini'")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or not (v.startswith("sqlite") or v.startswith("postgresql")):
            raise ValueError(
                f"Invalid DATABASE_URL scheme '{v}'. Must start with 'postgresql' or 'sqlite'."
            )
        return v


settings = Settings()
