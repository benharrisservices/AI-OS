"""Integration configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IntegrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    retry_attempts: int = Field(default=3, alias="INTEGRATION_RETRY_ATTEMPTS")
    retry_backoff_seconds: float = Field(default=1.0, alias="INTEGRATION_RETRY_BACKOFF_SECONDS")
    health_timeout_seconds: float = Field(default=5.0, alias="INTEGRATION_HEALTH_TIMEOUT_SECONDS")

    schema_version: str = "1.0"


def get_integration_settings() -> IntegrationSettings:
    return IntegrationSettings()
