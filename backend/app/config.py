"""Application settings, loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    env: str = Field(default="development", alias="TROVE_ENV")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    # Public URL users reach Trove on; shown on the Info page (API / MCP endpoints).
    public_url: str = Field(default="http://localhost:8080", alias="TROVE_PUBLIC_URL")

    # Build metadata (baked into the image at build time)
    app_version: str = Field(default="dev", alias="TROVE_VERSION")
    git_commit: str = Field(default="unknown", alias="TROVE_GIT_COMMIT")
    build_time: str = Field(default="unknown", alias="TROVE_BUILD_TIME")

    # Database
    postgres_user: str = Field(default="trove", alias="POSTGRES_USER")
    postgres_password: str = Field(default="trove", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="trove", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    # Open a fresh connection per session instead of pooling (tests; always on for SQLite).
    db_null_pool: bool = Field(default=False, alias="DB_NULL_POOL")

    # Auth
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    # Let candidates create their own accounts from the login page.
    allow_candidate_registration: bool = Field(
        default=True, alias="ALLOW_CANDIDATE_REGISTRATION"
    )

    # Bootstrap headhunter (created on startup if it does not exist)
    bootstrap_headhunter_email: str = Field(
        default="headhunter@example.com", alias="BOOTSTRAP_HEADHUNTER_EMAIL"
    )
    bootstrap_headhunter_password: str = Field(
        default="change-me-please", alias="BOOTSTRAP_HEADHUNTER_PASSWORD"
    )

    # Uploads
    max_upload_mb: int = Field(default=10, alias="MAX_UPLOAD_MB")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL used by the app."""
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Sync URL used by Alembic migrations."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
