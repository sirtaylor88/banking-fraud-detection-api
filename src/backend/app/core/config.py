"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings populated from .env.local or environment variables."""

    # * Environment settings
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    model_config = SettingsConfigDict(
        env_file="../../.envs/.env.local",
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
    DATABASE_URL: str = ""

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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:  # pylint: disable=invalid-name
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
