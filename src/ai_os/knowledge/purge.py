"""Source purge: remove documents and index entries without full rebuild."""

from __future__ import annotations

import shutil
from pathlib import Path

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.embedding import EmbeddingService
from ai_os.knowledge.index.keyword import KeywordIndex
from ai_os.knowledge.index.manifest import ManifestService
from ai_os.knowledge.index.vector import VectorIndex
from ai_os.knowledge.io import read_jsonl
from ai_os.knowledge.models import ChunkRecord, SourceStatus, utc_now
from ai_os.knowledge.registry import SourceRegistry


class PurgeService:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.registry = SourceRegistry(settings)
        self.vector = VectorIndex(settings)
        self.keyword = KeywordIndex(settings)
        self.embedder = EmbeddingService(settings)
        self.manifest = ManifestService(settings)

    def purge_source(self, source_id: str, *, delete_raw: bool = False) -> None:
        record = self.registry.get(source_id)
        if record is None:
            raise ValueError(f"Unknown source: {source_id}")

        for doc_id in list(record.doc_ids):
            self._purge_document(doc_id, source_id)

        if delete_raw:
            raw_dir = self.settings.knowledge_raw_dir / source_id
            if raw_dir.exists():
                shutil.rmtree(raw_dir)

        record.status = SourceStatus.TOMBSTONED
        record.doc_ids = []
        record.updated_at = utc_now()
        self.registry.upsert(record)
        self._refresh_manifest()

    def purge_document(self, doc_id: str) -> None:
        source_id = self._source_id_for_doc(doc_id)
        self._purge_document(doc_id, source_id)
        self._refresh_manifest()

    def _purge_document(self, doc_id: str, source_id: str | None) -> None:
        doc_dir = self.settings.knowledge_processed_dir / "documents" / doc_id
        chunks = self._load_chunks(doc_dir)
        content_hashes = [c.content_hash for c in chunks if c.chunk_level.value == "child"]
        chunk_ids = [c.chunk_id for c in chunks if c.chunk_level.value == "child"]

        self.vector.delete_doc(doc_id)
        if source_id:
            self.vector.delete_source(source_id)
        self.keyword.delete_doc(doc_id)
        self.embedder.purge_cache_hashes(content_hashes)

        if doc_dir.exists():
            shutil.rmtree(doc_dir)

    def _source_id_for_doc(self, doc_id: str) -> str | None:
        meta_path = self.settings.knowledge_processed_dir / "documents" / doc_id / "document.meta.json"
        if not meta_path.exists():
            return None
        from ai_os.knowledge.io import read_json

        return read_json(meta_path).get("source_id")

    def _load_chunks(self, doc_dir: Path) -> list[ChunkRecord]:
        path = doc_dir / "chunks.jsonl"
        if not path.exists():
            return []
        return [ChunkRecord.model_validate(row) for row in read_jsonl(path)]

    def _refresh_manifest(self) -> None:
        from ai_os.knowledge.index.manifest import ManifestService
        from ai_os.knowledge.io import read_jsonl
        from ai_os.knowledge.models import ChunkRecord, EmbeddingRecord, SourceStatus

        registry = SourceRegistry(self.settings)
        registry_records = [
            r for r in registry._load_all() if r.status != SourceStatus.TOMBSTONED
        ]
        docs_root = self.settings.knowledge_processed_dir / "documents"
        doc_dirs = [d for d in docs_root.glob("*") if d.is_dir()] if docs_root.exists() else []
        chunks: list[ChunkRecord] = []
        embeddings: list[EmbeddingRecord] = []
        for doc_dir in doc_dirs:
            for row in read_jsonl(doc_dir / "chunks.jsonl"):
                chunk = ChunkRecord.model_validate(row)
                if chunk.chunk_level.value == "child":
                    chunks.append(chunk)
            for row in read_jsonl(doc_dir / "embeddings.jsonl"):
                embeddings.append(EmbeddingRecord.model_validate(row))
        ManifestService(self.settings).save(
            source_count=len(registry_records),
            document_count=len(doc_dirs),
            chunk_count=len(chunks),
            child_chunk_count=len(chunks),
            embedding_count=len(embeddings),
        )
