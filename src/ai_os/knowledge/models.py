"""Pydantic models for Knowledge Engine records."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Format(str, Enum):
    MARKDOWN = "markdown"
    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    URL = "url"


class SourceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    TOMBSTONED = "tombstoned"
    UNCHANGED = "unchanged"


class ExtractionQuality(str, Enum):
    FULL = "full"
    DEGRADED = "degraded"
    FAILED = "failed"


class ChunkLevel(str, Enum):
    PARENT = "parent"
    CHILD = "child"


class IntakeChannel(str, Enum):
    DROP = "drop"
    WATCH = "watch"
    CLI = "cli"
    API = "api"
    PROMOTION = "promotion"


class ErrorRecord(BaseModel):
    code: str
    message: str
    stage: str
    retryable: bool = False
    occurred_at: datetime = Field(default_factory=utc_now)
    details: dict[str, Any] = Field(default_factory=dict)


class IntakeRecord(BaseModel):
    schema_version: str = "1.0"
    source_id: str
    kind: str
    path_or_url: str
    format: Format
    fingerprint: str
    original_filename: str | None = None
    mime_type: str | None = None
    byte_size: int = 0
    tags: list[str] = Field(default_factory=list)
    operator_metadata: dict[str, Any] = Field(default_factory=dict)
    intake_channel: IntakeChannel = IntakeChannel.CLI
    intaked_at: datetime = Field(default_factory=utc_now)
    final_url: str | None = None
    http_status: int | None = None
    fetched_at: datetime | None = None
    content_type: str | None = None


class SourceRegistryRecord(BaseModel):
    schema_version: str = "1.0"
    source_id: str
    status: SourceStatus
    format: Format
    fingerprint: str
    fingerprint_algorithm: str = "sha256"
    original_filename: str | None = None
    original_uri: str
    byte_size: int = 0
    doc_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    intake_channel: IntakeChannel = IntakeChannel.CLI
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_job_id: str | None = None
    error: ErrorRecord | None = None


class ExtractedDocument(BaseModel):
    title: str
    body: str
    language: str = "en"
    extraction_quality: ExtractionQuality = ExtractionQuality.FULL
    page_count: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    schema_version: str = "1.0"
    pipeline_version: str = "1.0.0"
    doc_id: str
    source_id: str
    title: str
    language: str = "en"
    format: Format
    extraction_quality: ExtractionQuality = ExtractionQuality.FULL
    page_count: int | None = None
    word_count: int = 0
    char_count: int = 0
    heading_count: int = 0
    chunk_count: int = 0
    parent_count: int = 0
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    source_uri: str
    raw_path: str
    processed_path: str
    custom: dict[str, Any] = Field(default_factory=dict)


class ChunkRecord(BaseModel):
    schema_version: str = "1.0"
    chunk_id: str
    doc_id: str
    source_id: str
    chunk_level: ChunkLevel
    parent_chunk_id: str | None = None
    chunk_index: int
    heading_path: str
    title: str
    language: str = "en"
    token_count: int = 0
    char_count: int = 0
    content_hash: str
    embed_text: str
    body_text: str
    start_offset: int = 0
    end_offset: int = 0
    page_start: int | None = None
    page_end: int | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class EmbeddingRecord(BaseModel):
    schema_version: str = "1.0"
    chunk_id: str
    doc_id: str
    content_hash: str
    embedding_model: str
    embedding_provider: str
    embedding_dimensions: int
    vector: list[float]
    embedded_at: datetime = Field(default_factory=utc_now)
    cache_hit: bool = False


class IndexManifest(BaseModel):
    schema_version: str = "1.0"
    index_version: str = "1"
    pipeline_version: str = "1.0.0"
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    vector_store: str
    vector_store_path: str
    keyword_index_path: str
    source_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    child_chunk_count: int = 0
    last_full_rebuild_at: datetime | None = None
    last_incremental_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SearchHit(BaseModel):
    chunk_id: str
    doc_id: str
    source_id: str
    score: float
    scores: dict[str, float] = Field(default_factory=dict)
    title: str
    heading_path: str
    excerpt: str
    source_uri: str


class SearchQuery(BaseModel):
    query: str
    mode: str = "hybrid"
    top_k: int = 10
    filters: dict[str, Any] = Field(default_factory=dict)
