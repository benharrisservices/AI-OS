"""Index manifest management."""

from __future__ import annotations

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.io import read_json, write_json
from ai_os.knowledge.models import IndexManifest, utc_now


class ManifestService:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.path = settings.knowledge_index_dir / "manifest.json"

    def load(self) -> IndexManifest:
        if not self.path.exists():
            return IndexManifest(
                embedding_provider=self.settings.embedding_provider,
                embedding_model=self.settings.embedding_model,
                embedding_dimensions=self.settings.embedding_dimensions,
                vector_store=self.settings.vector_store,
                vector_store_path=str(self.settings.vector_store_path),
                keyword_index_path=str(self.settings.knowledge_index_dir / "keyword"),
            )
        return IndexManifest.model_validate(read_json(self.path))

    def save(
        self,
        *,
        source_count: int,
        document_count: int,
        chunk_count: int,
        child_chunk_count: int,
        embedding_count: int = 0,
        full_rebuild: bool = False,
        last_ingest_at=None,
        last_reindex_at=None,
    ) -> IndexManifest:
        manifest = self.load()
        manifest.embedding_provider = self.settings.embedding_provider
        manifest.embedding_model = self.settings.embedding_model
        manifest.embedding_dimensions = self.settings.embedding_dimensions
        manifest.vector_store = self.settings.vector_store
        manifest.vector_store_path = str(self.settings.vector_store_path)
        manifest.keyword_index_path = str(self.settings.knowledge_index_dir / "keyword")
        manifest.source_count = source_count
        manifest.document_count = document_count
        manifest.chunk_count = chunk_count
        manifest.child_chunk_count = child_chunk_count
        manifest.embedding_count = embedding_count
        manifest.updated_at = utc_now()
        if full_rebuild:
            manifest.last_full_rebuild_at = utc_now()
        if last_reindex_at is not None:
            manifest.last_incremental_at = last_reindex_at
        elif full_rebuild:
            manifest.last_incremental_at = utc_now()
        elif last_ingest_at is not None:
            manifest.last_incremental_at = last_ingest_at
        write_json(self.path, manifest)
        if last_ingest_at is not None:
            ingest_path = self.settings.knowledge_index_dir / ".last_ingest"
            ingest_path.write_text(last_ingest_at.isoformat(), encoding="utf-8")
        if last_reindex_at is not None:
            reindex_path = self.settings.knowledge_index_dir / ".last_reindex"
            reindex_path.write_text(last_reindex_at.isoformat(), encoding="utf-8")
        return manifest

    def last_ingest_at(self):
        path = self.settings.knowledge_index_dir / ".last_ingest"
        if not path.exists():
            return None
        from datetime import datetime

        return datetime.fromisoformat(path.read_text(encoding="utf-8").strip())

    def last_reindex_at(self):
        path = self.settings.knowledge_index_dir / ".last_reindex"
        if path.exists():
            from datetime import datetime

            return datetime.fromisoformat(path.read_text(encoding="utf-8").strip())
        manifest = self.load()
        return manifest.last_full_rebuild_at or manifest.last_incremental_at
