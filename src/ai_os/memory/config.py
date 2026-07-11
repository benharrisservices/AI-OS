"""Memory System configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default=Path("./memory"), alias="AI_OS_DATA_DIR")
    working_dir: Path = Field(default=Path("./memory/working"), alias="MEMORY_WORKING_DIR")
    episodic_dir: Path = Field(default=Path("./memory/episodic"), alias="MEMORY_EPISODIC_DIR")
    semantic_dir: Path = Field(default=Path("./memory/semantic"), alias="MEMORY_SEMANTIC_DIR")
    procedural_dir: Path = Field(default=Path("./memory/procedural"), alias="MEMORY_PROCEDURAL_DIR")

    retention_days: int = Field(default=90, alias="MEMORY_RETENTION_DAYS")
    working_ttl_minutes: int = Field(default=60, alias="MEMORY_WORKING_TTL_MINUTES")
    max_retrieval_items: int = Field(default=10, alias="MEMORY_MAX_RETRIEVAL_ITEMS")

    schema_version: str = "1.0"
    memory_version: str = "1.0.0"

    def ensure_dirs(self) -> None:
        for path in (
            self.working_dir,
            self.episodic_dir,
            self.semantic_dir,
            self.procedural_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def get_memory_settings() -> MemorySettings:
    return MemorySettings()
