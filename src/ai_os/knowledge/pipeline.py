"""End-to-end knowledge pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

from ai_os.knowledge.chunking import chunk_document
from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.embedding import EmbeddingService
from ai_os.knowledge.extractors import extract_document
from ai_os.knowledge.extractors.bootstrap import register_builtin_extractors
from ai_os.knowledge.ids import new_doc_id
from ai_os.knowledge.incremental import (
    build_processing_state,
    diff_chunks,
    merge_embeddings,
    needs_reprocess,
)
from ai_os.knowledge.index.keyword import KeywordIndex
from ai_os.knowledge.index.manifest import ManifestService
from ai_os.knowledge.index.vector import VectorIndex
from ai_os.knowledge.intake import IntakeService
from ai_os.knowledge.io import append_jsonl, read_json, read_jsonl, write_json, write_jsonl
from ai_os.knowledge.metadata import build_document_record
from ai_os.knowledge.models import (
    ChunkRecord,
    DocumentRecord,
    EmbeddingRecord,
    ErrorRecord,
    ExtractionQuality,
    Format,
    IntakeRecord,
    ProcessingState,
    SourceRegistryRecord,
    SourceStatus,
    utc_now,
)
from ai_os.knowledge.normalize import build_document_markdown, enrich_extracted
from ai_os.knowledge.registry import SourceRegistry

EXTENSION_BY_FORMAT = {
    Format.MARKDOWN: ".md",
    Format.TXT: ".txt",
    Format.PDF: ".pdf",
    Format.DOCX: ".docx",
    Format.HTML: ".html",
    Format.URL: ".html",
}


class KnowledgePipeline:
    def __init__(self, settings: KnowledgeSettings | None = None) -> None:
        self.settings = settings or KnowledgeSettings()
        self.settings.ensure_dirs()
        register_builtin_extractors()
        self.intake = IntakeService(self.settings)
        self.registry = SourceRegistry(self.settings)
        self.embedder = EmbeddingService(self.settings)
        self.vector = VectorIndex(self.settings)
        self.keyword = KeywordIndex(self.settings)
        self.manifest = ManifestService(self.settings)

    def ingest_file(self, path: Path, tags: list[str] | None = None) -> SourceRegistryRecord:
        record = self.intake.ingest_file(path, tags=tags)
        if record.status != SourceStatus.UNCHANGED:
            self.process_source(record.source_id)
            record = self.registry.get(record.source_id) or record
        return record

    def ingest_url(self, url: str, tags: list[str] | None = None) -> SourceRegistryRecord:
        record = self.intake.ingest_url(url, tags=tags)
        if record.status != SourceStatus.UNCHANGED:
            self.process_source(record.source_id)
            record = self.registry.get(record.source_id) or record
        return record

    def process_source(self, source_id: str, *, force: bool = False) -> DocumentRecord:
        record = self.registry.get(source_id)
        if record is None:
            raise ValueError(f"Unknown source: {source_id}")

        raw_dir = self.settings.knowledge_raw_dir / source_id
        intake = IntakeRecord.model_validate(read_json(raw_dir / "intake.json"))
        doc_id = record.doc_ids[0] if record.doc_ids else new_doc_id(source_id)
        doc_dir = self.settings.knowledge_processed_dir / "documents" / doc_id
        state = self._load_processing_state(doc_dir)

        if (
            not force
            and state is not None
            and not needs_reprocess(
                state,
                source_fingerprint=intake.fingerprint,
                pipeline_version=self.settings.pipeline_version,
            )
        ):
            record.status = SourceStatus.READY
            self.registry.upsert(record)
            meta_path = doc_dir / "document.meta.json"
            if meta_path.exists():
                return DocumentRecord.model_validate(read_json(meta_path))
            return self._process_source_inner(record, source_id, intake, doc_id, force=True)

        return self._process_source_inner(record, source_id, intake, doc_id, force=force)

    def _process_source_inner(
        self,
        record: SourceRegistryRecord,
        source_id: str,
        intake: IntakeRecord,
        doc_id: str,
        *,
        force: bool,
    ) -> DocumentRecord:
        record.status = SourceStatus.PROCESSING
        self.registry.upsert(record)

        try:
            raw_dir = self.settings.knowledge_raw_dir / source_id
            fmt = intake.format
            ext = EXTENSION_BY_FORMAT.get(fmt, ".bin")
            if fmt == Format.URL:
                data = (raw_dir / "snapshot.html").read_bytes()
            else:
                data = (raw_dir / f"original{ext}").read_bytes()

            extracted = extract_document(data, fmt, path=Path(intake.original_filename or ""))
            extracted = enrich_extracted(extracted)
            if extracted.extraction_quality == ExtractionQuality.FAILED:
                raise RuntimeError("EXTRACT_EMPTY: no content extracted")

            document = build_document_record(
                doc_id=doc_id,
                source_id=source_id,
                intake=intake,
                extracted=extracted,
                fmt=fmt,
                settings_pipeline_version=self.settings.pipeline_version,
            )

            doc_dir = self.settings.knowledge_processed_dir / "documents" / doc_id
            doc_dir.mkdir(parents=True, exist_ok=True)
            markdown = build_document_markdown(document, extracted.body)
            (doc_dir / "document.md").write_text(markdown, encoding="utf-8")
            write_json(doc_dir / "document.meta.json", document)
            append_jsonl(self.settings.knowledge_processed_dir / ".catalog" / "documents.jsonl", document)

            old_chunks = self._load_chunks(doc_dir)
            new_chunks = chunk_document(document, extracted.body, self.settings)
            document.chunk_count = len(new_chunks)
            document.parent_count = sum(1 for c in new_chunks if c.chunk_level.value == "parent")
            document.updated_at = utc_now()
            write_json(doc_dir / "document.meta.json", document)
            write_jsonl(doc_dir / "chunks.jsonl", new_chunks)

            diff = diff_chunks(old_chunks, new_chunks)
            existing_embeddings = {
                e.chunk_id: e for e in self._load_embeddings(doc_dir)
            }
            to_embed = diff.added + diff.changed
            fresh_embeddings = self.embedder.embed_chunk_list(to_embed) if to_embed else []
            embeddings = merge_embeddings(diff, existing_embeddings, fresh_embeddings)
            write_jsonl(doc_dir / "embeddings.jsonl", embeddings)

            if diff.removed_ids:
                self.vector.delete_chunks(diff.removed_ids)
                self.keyword.delete_chunks(diff.removed_ids)
                removed_hashes = [
                    c.content_hash
                    for c in old_chunks
                    if c.chunk_id in diff.removed_ids and c.chunk_level.value == "child"
                ]
                self.embedder.purge_cache_hashes(removed_hashes)

            index_chunks = diff.added + diff.changed
            index_embeddings = [
                e for e in embeddings if e.chunk_id in {c.chunk_id for c in index_chunks}
            ]
            if index_chunks:
                self.vector.upsert(index_chunks, index_embeddings)
                self.keyword.upsert_chunks(index_chunks)
            elif not old_chunks:
                self.vector.upsert(new_chunks, embeddings)
                self.keyword.upsert_chunks(new_chunks)

            processing_state = build_processing_state(
                doc_id=doc_id,
                source_id=source_id,
                source_fingerprint=intake.fingerprint,
                pipeline_version=self.settings.pipeline_version,
                chunks=new_chunks,
            )
            write_json(doc_dir / "processing_state.json", processing_state)
            self._update_manifest(last_ingest_at=utc_now())

            record.status = SourceStatus.READY
            record.doc_ids = [doc_id]
            record.error = None
            self.registry.upsert(record)
            return document

        except Exception as exc:
            record.status = SourceStatus.FAILED
            record.error = ErrorRecord(
                code="PROCESS_FAILED",
                message=str(exc),
                stage="process",
                retryable=False,
            )
            self.registry.upsert(record)
            raise

    def process_all_pending(self) -> list[DocumentRecord]:
        results: list[DocumentRecord] = []
        for record in self.registry._load_all():
            if record.status in {SourceStatus.PENDING, SourceStatus.FAILED}:
                results.append(self.process_source(record.source_id))
        return results

    def reindex_all(self) -> None:
        all_chunks = self._load_all_child_chunks()
        all_embeddings = self._load_all_embeddings()
        embedding_by_chunk = {e.chunk_id: e for e in all_embeddings}

        vector_ids = set(self.vector.list_ids())
        expected_ids = {c.chunk_id for c in all_chunks}
        stale_ids = list(vector_ids - expected_ids)
        if stale_ids:
            self.vector.delete_chunks(stale_ids)

        for doc_dir in (self.settings.knowledge_processed_dir / "documents").iterdir():
            if not doc_dir.is_dir():
                continue
            doc_id = doc_dir.name
            chunks_path = doc_dir / "chunks.jsonl"
            if not chunks_path.exists():
                continue
            chunks = [ChunkRecord.model_validate(row) for row in read_jsonl(chunks_path)]
            embeddings = [
                embedding_by_chunk[c.chunk_id]
                for c in chunks
                if c.chunk_id in embedding_by_chunk
            ]
            self.vector.delete_doc(doc_id)
            self.vector.upsert(chunks, embeddings)

        self.keyword.rebuild(all_chunks)
        self._update_manifest(full_rebuild=True, last_reindex_at=utc_now())

    def ingest_directory(self, directory: Path, *, tags: list[str] | None = None) -> list[SourceRegistryRecord]:
        directory = directory.expanduser().resolve()
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        supported = {".md", ".markdown", ".txt", ".pdf", ".docx", ".html", ".htm"}
        records: list[SourceRegistryRecord] = []
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix.lower() in supported:
                records.append(self.ingest_file(path, tags=tags))
        return records

    def _load_processing_state(self, doc_dir: Path) -> ProcessingState | None:
        path = doc_dir / "processing_state.json"
        if not path.exists():
            return None
        return ProcessingState.model_validate(read_json(path))

    def _load_chunks(self, doc_dir: Path) -> list[ChunkRecord]:
        path = doc_dir / "chunks.jsonl"
        if not path.exists():
            return []
        return [ChunkRecord.model_validate(row) for row in read_jsonl(path)]

    def _load_all_child_chunks(self) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        docs_root = self.settings.knowledge_processed_dir / "documents"
        if not docs_root.exists():
            return chunks
        for doc_dir in docs_root.iterdir():
            if not doc_dir.is_dir():
                continue
            for chunk in self._load_chunks(doc_dir):
                if chunk.chunk_level.value == "child":
                    chunks.append(chunk)
        return chunks

    def _load_embeddings(self, doc_dir: Path) -> list[EmbeddingRecord]:
        path = doc_dir / "embeddings.jsonl"
        if not path.exists():
            return []
        return [EmbeddingRecord.model_validate(row) for row in read_jsonl(path)]

    def _load_all_embeddings(self) -> list[EmbeddingRecord]:
        embeddings: list[EmbeddingRecord] = []
        docs_root = self.settings.knowledge_processed_dir / "documents"
        if not docs_root.exists():
            return embeddings
        for doc_dir in docs_root.iterdir():
            if not doc_dir.is_dir():
                continue
            embeddings.extend(self._load_embeddings(doc_dir))
        return embeddings

    def _update_manifest(
        self,
        *,
        full_rebuild: bool = False,
        last_ingest_at=None,
        last_reindex_at=None,
    ) -> None:
        registry_records = [
            r for r in self.registry._load_all() if r.status != SourceStatus.TOMBSTONED
        ]
        doc_dirs = [
            d
            for d in (self.settings.knowledge_processed_dir / "documents").glob("*")
            if d.is_dir()
        ]
        chunks = self._load_all_child_chunks()
        embeddings = self._load_all_embeddings()
        manifest = self.manifest.save(
            source_count=len(registry_records),
            document_count=len(doc_dirs),
            chunk_count=len(chunks),
            child_chunk_count=len(chunks),
            embedding_count=len(embeddings),
            full_rebuild=full_rebuild,
            last_ingest_at=last_ingest_at,
            last_reindex_at=last_reindex_at,
        )
        return manifest
