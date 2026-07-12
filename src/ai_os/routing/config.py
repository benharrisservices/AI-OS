"""Model routing configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RoutingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    default_provider: str = Field(default="ollama", alias="MODEL_ROUTER_DEFAULT_PROVIDER")
    fallback_chain: str = Field(
        default="ollama,openai,anthropic,gemini,groq,openrouter",
        alias="MODEL_ROUTER_FALLBACK_CHAIN",
    )
    prefer_local: bool = Field(default=True, alias="MODEL_ROUTER_PREFER_LOCAL")

    schema_version: str = "1.0"


def get_routing_settings() -> RoutingSettings:
    return RoutingSettings()
