"""Agent Runtime configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tasks_dir: Path = Field(default=Path("./memory/agent/tasks"), alias="AGENT_TASKS_DIR")
    logs_dir: Path = Field(default=Path("./memory/agent/logs"), alias="AGENT_LOGS_DIR")
    workflows_dir: Path = Field(default=Path("./config/workflows"), alias="AGENT_WORKFLOWS_DIR")
    agents_dir: Path = Field(default=Path("./config/agents"), alias="AGENT_DEFINITIONS_DIR")

    default_max_retries: int = Field(default=3, alias="AGENT_DEFAULT_MAX_RETRIES")
    shell_enabled: bool = Field(default=False, alias="AGENT_SHELL_ENABLED")
    http_enabled: bool = Field(default=True, alias="AGENT_HTTP_ENABLED")

    schema_version: str = "1.0"
    runtime_version: str = "1.0.0"

    def ensure_dirs(self) -> None:
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir.mkdir(parents=True, exist_ok=True)


def get_agent_settings() -> AgentSettings:
    return AgentSettings()
