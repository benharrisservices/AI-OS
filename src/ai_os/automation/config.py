"""Automation Layer configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AutomationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    automations_dir: Path = Field(
        default=Path("./config/automations"),
        alias="AUTOMATION_DEFINITIONS_DIR",
    )
    history_dir: Path = Field(
        default=Path("./memory/automation/history"),
        alias="AUTOMATION_HISTORY_DIR",
    )
    state_dir: Path = Field(
        default=Path("./memory/automation/state"),
        alias="AUTOMATION_STATE_DIR",
    )
    default_timeout_seconds: int = Field(default=300, alias="AUTOMATION_DEFAULT_TIMEOUT_SECONDS")
    default_backoff_seconds: int = Field(default=60, alias="AUTOMATION_DEFAULT_BACKOFF_SECONDS")
    tick_interval_seconds: int = Field(default=60, alias="AUTOMATION_TICK_INTERVAL_SECONDS")

    schema_version: str = "1.0"
    automation_version: str = "1.0.0"

    def ensure_dirs(self) -> None:
        self.automations_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)


def get_automation_settings() -> AutomationSettings:
    return AutomationSettings()
