"""Read access to processed documents and chunks."""

from __future__ import annotations

from pathlib import Path

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.io import read_json, read_jsonl
from ai_os.knowledge.models import ChunkRecord, DocumentRecord


class ChunkStore:
    """Loads processed documents and chunks with small in-memory caches."""

    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self._doc_cache: dict[str, DocumentRecord | None] = {}
        self._chunk_cache: dict[str, dict[str, ChunkRecord]] = {}

    def _doc_dir(self, doc_id: str) -> Path:
        return self.settings.knowledge_processed_dir / "documents" / doc_id

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        if doc_id in self._doc_cache:
            return self._doc_cache[doc_id]
        meta_path = self._doc_dir(doc_id) / "document.meta.json"
        document = DocumentRecord.model_validate(read_json(meta_path)) if meta_path.exists() else None
        self._doc_cache[doc_id] = document
        return document

    def _chunks_for_doc(self, doc_id: str) -> dict[str, ChunkRecord]:
        if doc_id in self._chunk_cache:
            return self._chunk_cache[doc_id]
        chunks_path = self._doc_dir(doc_id) / "chunks.jsonl"
        mapping: dict[str, ChunkRecord] = {}
        for row in read_jsonl(chunks_path):
            chunk = ChunkRecord.model_validate(row)
            mapping[chunk.chunk_id] = chunk
        self._chunk_cache[doc_id] = mapping
        return mapping

    def get_chunk(self, doc_id: str, chunk_id: str) -> ChunkRecord | None:
        return self._chunks_for_doc(doc_id).get(chunk_id)

    def get_source_uri(self, doc_id: str) -> str | None:
        document = self.get_document(doc_id)
        return document.source_uri if document else None

    def get_title(self, doc_id: str) -> str | None:
        document = self.get_document(doc_id)
        return document.title if document else None
