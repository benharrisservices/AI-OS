"""Knowledge Engine configuration."""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class KnowledgeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Persistent data root (Railway volume in production, e.g. /data). When set,
    # the relative knowledge paths below are rooted under it so imports persist.
    ai_os_data_dir: Path | None = Field(default=None, alias="AI_OS_DATA_DIR")

    # Paths
    knowledge_raw_dir: Path = Field(default=Path("./knowledge/raw"), alias="KNOWLEDGE_RAW_DIR")
    knowledge_processed_dir: Path = Field(
        default=Path("./knowledge/processed"), alias="KNOWLEDGE_PROCESSED_DIR"
    )
    knowledge_index_dir: Path = Field(default=Path("./knowledge/index"), alias="KNOWLEDGE_INDEX_DIR")

    # Chunking
    knowledge_chunk_size: int = Field(default=512, alias="KNOWLEDGE_CHUNK_SIZE")
    knowledge_chunk_overlap: int = Field(default=64, alias="KNOWLEDGE_CHUNK_OVERLAP")
    knowledge_max_file_size_mb: int = Field(default=50, alias="KNOWLEDGE_MAX_FILE_SIZE_MB")
    parent_max_tokens: int = 2048
    min_chunk_tokens: int = 32

    # Embeddings (local-first via Ollama)
    embedding_provider: str = Field(default="ollama", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="nomic-embed-text", alias="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=768, alias="EMBEDDING_DIMENSIONS")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    ollama_host: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_HOST")
    # OpenAI embeddings — used automatically when Ollama is unavailable (production).
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    openai_embedding_dimensions: int = Field(
        default=1536, alias="OPENAI_EMBEDDING_DIMENSIONS"
    )

    # Vector store
    vector_store: str = Field(default="chroma", alias="VECTOR_STORE")
    vector_store_path: Path = Field(default=Path("./knowledge/index/vectors"), alias="VECTOR_STORE_PATH")

    # Search
    vector_top_k: int = 20
    keyword_top_k: int = 20
    hybrid_rrf_k: int = 60
    search_top_k: int = 10

    # Pipeline
    pipeline_version: str = "1.0.0"
    schema_version: str = "1.0"

    # URL intake
    url_timeout_seconds: int = 30
    url_max_redirects: int = 5
    url_user_agent: str = "AI-OS-KnowledgeBot/1.0"

    # Watch / maintenance
    knowledge_watch_dir: Path = Field(default=Path("./knowledge/raw/inbox"), alias="KNOWLEDGE_WATCH_DIR")
    knowledge_backup_dir: Path = Field(default=Path("./knowledge/backups"), alias="KNOWLEDGE_BACKUP_DIR")
    watch_debounce_seconds: float = 2.0

    @model_validator(mode="after")
    def _root_paths_under_data_dir(self) -> "KnowledgeSettings":
        """Root relative knowledge paths under AI_OS_DATA_DIR when it is set.

        Production sets AI_OS_DATA_DIR=/data (the Railway volume), so imported
        documents, indexes and caches persist there across redeploys. Absolute
        overrides and local development (no AI_OS_DATA_DIR) are left unchanged.
        """
        base = self.ai_os_data_dir
        # Only re-root under an absolute mount (production /data volume). A
        # relative or unset AI_OS_DATA_DIR (local development) is left untouched.
        if base is None or not base.is_absolute():
            return self
        for attr in (
            "knowledge_raw_dir",
            "knowledge_processed_dir",
            "knowledge_index_dir",
            "vector_store_path",
            "knowledge_watch_dir",
            "knowledge_backup_dir",
        ):
            value: Path = getattr(self, attr)
            if not value.is_absolute():
                object.__setattr__(self, attr, base / value)
        return self

    def ensure_dirs(self) -> None:
        for path in (
            self.knowledge_raw_dir,
            self.knowledge_raw_dir / ".registry",
            self.knowledge_raw_dir / "inbox",
            self.knowledge_raw_dir / "uploads",
            self.knowledge_processed_dir,
            self.knowledge_processed_dir / ".catalog",
            self.knowledge_processed_dir / ".jobs",
            self.knowledge_index_dir,
            self.knowledge_index_dir / "embeddings" / "cache",
            self.knowledge_index_dir / "keyword",
            self.vector_store_path,
            self.knowledge_backup_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def get_settings() -> KnowledgeSettings:
    return KnowledgeSettings()
