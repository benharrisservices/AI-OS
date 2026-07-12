"""Knowledge Engine configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KnowledgeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

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

    def ensure_dirs(self) -> None:
        for path in (
            self.knowledge_raw_dir,
            self.knowledge_raw_dir / ".registry",
            self.knowledge_raw_dir / "inbox",
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
