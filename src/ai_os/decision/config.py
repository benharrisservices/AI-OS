"""Decision Engine configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DecisionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    decisions_dir: Path = Field(default=Path("./memory/decisions"), alias="DECISION_ENGINE_DECISIONS_DIR")
    prompts_dir: Path = Field(default=Path("./decision-engine/prompts"), alias="DECISION_ENGINE_PROMPTS_DIR")
    templates_dir: Path = Field(
        default=Path("./decision-engine/templates"), alias="DECISION_ENGINE_TEMPLATES_DIR"
    )

    default_strategy: str = Field(default="analytical", alias="DECISION_ENGINE_DEFAULT_STRATEGY")
    default_temperature: float = Field(default=0.2, alias="DECISION_ENGINE_DEFAULT_TEMPERATURE")
    max_tokens: int = Field(default=4096, alias="DECISION_ENGINE_MAX_TOKENS")
    timeout_seconds: int = Field(default=120, alias="DECISION_ENGINE_TIMEOUT_SECONDS")

    # LLM provider (local-first via Ollama; cloud optional in future)
    llm_provider: str = Field(default="ollama", alias="DECISION_ENGINE_LLM_PROVIDER")
    llm_model: str = Field(default="llama3.2", alias="OLLAMA_DEFAULT_MODEL")
    ollama_host: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_HOST")
    use_llm: bool = Field(default=True, alias="DECISION_ENGINE_USE_LLM")

    schema_version: str = "1.0"
    engine_version: str = "1.0.0"

    def ensure_dirs(self) -> None:
        self.decisions_dir.mkdir(parents=True, exist_ok=True)


def get_decision_settings() -> DecisionSettings:
    return DecisionSettings()
