"""Capability Layer configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CapabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    skills_dir: Path = Field(default=Path("./config/skills"), alias="CAPABILITY_SKILLS_DIR")
    default_confidence_threshold: float = Field(default=0.5, alias="CAPABILITY_CONFIDENCE_THRESHOLD")

    schema_version: str = "1.0"
    capability_version: str = "1.0.0"

    def ensure_dirs(self) -> None:
        self.skills_dir.mkdir(parents=True, exist_ok=True)


def get_capability_settings() -> CapabilitySettings:
    return CapabilitySettings()
