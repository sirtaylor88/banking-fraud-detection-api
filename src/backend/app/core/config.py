"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# src/.envs/.env.local, resolved from this file so it loads from any working dir.
ENV_FILE = Path(__file__).resolve().parents[3] / ".envs" / ".env.local"


class Settings(BaseSettings):
    """Application settings populated from .env.local or environment variables."""

    # * Environment settings
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )

    # * API settings
    API_V1_STR: str = ""

    # * Project settings
    PROJECT_NAME: str = ""
    PROJECT_DESCRIPTION: str = ""
    SITE_NAME: str = ""

    # * Database settings
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_HOST: str = Field(default="postgres-db", min_length=1)
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_SCHEMA: str = ""  # set as search_path; empty keeps the server default

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build the async database URL from the POSTGRES_* settings.

        The schema is not part of the URL (asyncpg rejects unknown connection
        parameters); it is applied as ``search_path`` via ``db_connect_args``.

        Returns:
            str: The DSN, e.g. ``postgresql+asyncpg://user:pass@postgres-db:5432/db``,
            with the password URL-escaped.
        """
        return URL.create(
            "postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    # ! Important: For the SMTP, redis and RabbitMQ hosts, use same service names
    # ! declared as in docker-compose.yml

    # * Email settings
    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = ""
    SMTP_HOST: str = Field(default="mailpit", min_length=1)
    SMTP_PORT: int = Field(default=1025, ge=1, le=65535)
    MAILPIT_UI_PORT: int = Field(default=8025, ge=1, le=65535)

    # * Redis settings
    REDIS_HOST: str = Field(default="redis", min_length=1)
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
    REDIS_DB: int = Field(default=0, ge=0, le=15)  # Redis has 16 DBs by default

    # * Auth
    OTP_EXPIRATION_MINUTES: int = 2 if ENVIRONMENT == "local" else 5
    LOGIN_ATTEMPTS: int = 3
    LOCKOUT_DURATION_IN_MINUTES: int = 2 if ENVIRONMENT == "local" else 5

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        """Build the Redis connection URL from the REDIS_* settings.

        Returns:
            str: The Redis URL, e.g. ``redis://redis:6379/0``.
        """
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # * RabbitMQ settings
    RABBITMQ_HOST: str = Field(default="rabbitmq", min_length=1)
    RABBITMQ_PORT: int = Field(default=5672, ge=1, le=65535)
    RABBITMQ_USER: str = Field(default="guest", min_length=1)
    RABBITMQ_PASSWORD: str = Field(default="guest", min_length=1)


settings = Settings()
