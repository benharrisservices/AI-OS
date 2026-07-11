"""End-to-end knowledge pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

from ai_os.knowledge.chunking import chunk_document
from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.embedding import EmbeddingService
from ai_os.knowledge.extractors import extract_document
from ai_os.knowledge.extractors.bootstrap import register_builtin_extractors
from ai_os.knowledge.format_detect import EXTENSION_MAP
from ai_os.knowledge.ids import new_doc_id
from ai_os.knowledge.index.keyword import KeywordIndex
from ai_os.knowledge.index.manifest import ManifestService
from ai_os.knowledge.index.vector import VectorIndex
from ai_os.knowledge.intake import IntakeService
from ai_os.knowledge.io import append_jsonl, read_json, write_json, write_jsonl
from ai_os.knowledge.metadata import build_document_record
from ai_os.knowledge.models import (
    ChunkRecord,
    DocumentRecord,
    ErrorRecord,
    ExtractionQuality,
    Format,
    IntakeRecord,
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

    def process_source(self, source_id: str) -> DocumentRecord:
        record = self.registry.get(source_id)
        if record is None:
            raise ValueError(f"Unknown source: {source_id}")

        record.status = SourceStatus.PROCESSING
        self.registry.upsert(record)

        try:
            raw_dir = self.settings.knowledge_raw_dir / source_id
            intake = IntakeRecord.model_validate(read_json(raw_dir / "intake.json"))
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

            doc_id = record.doc_ids[0] if record.doc_ids else new_doc_id(source_id)
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

            chunks = chunk_document(document, extracted.body, self.settings)
            document.chunk_count = len(chunks)
            document.parent_count = sum(1 for c in chunks if c.chunk_level.value == "parent")
            document.updated_at = utc_now()
            write_json(doc_dir / "document.meta.json", document)
            write_jsonl(doc_dir / "chunks.jsonl", chunks)

            embeddings = self.embedder.embed_chunks(chunks)
            write_jsonl(doc_dir / "embeddings.jsonl", embeddings)

            self.vector.delete_doc(doc_id)
            self.vector.upsert(chunks, embeddings)

            all_chunks = self._load_all_child_chunks()
            self.keyword.rebuild(all_chunks)
            self._update_manifest()

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

        for doc_dir in (self.settings.knowledge_processed_dir / "documents").glob("*"):
            doc_id = doc_dir.name
            self.vector.delete_doc(doc_id)
            chunks_path = doc_dir / "chunks.jsonl"
            if not chunks_path.exists():
                continue
            chunks = [ChunkRecord.model_validate(row) for row in self._read_jsonl(chunks_path)]
            embeddings = [embedding_by_chunk[c.chunk_id] for c in chunks if c.chunk_id in embedding_by_chunk]
            self.vector.upsert(chunks, embeddings)

        self.keyword.rebuild(all_chunks)
        self._update_manifest(full_rebuild=True)

    def _read_jsonl(self, path: Path) -> list[dict]:
        from ai_os.knowledge.io import read_jsonl

        return read_jsonl(path)

    def _load_all_child_chunks(self) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        docs_root = self.settings.knowledge_processed_dir / "documents"
        if not docs_root.exists():
            return chunks
        for doc_dir in docs_root.iterdir():
            chunks_path = doc_dir / "chunks.jsonl"
            if chunks_path.exists():
                for row in self._read_jsonl(chunks_path):
                    chunk = ChunkRecord.model_validate(row)
                    if chunk.chunk_level.value == "child":
                        chunks.append(chunk)
        return chunks

    def _load_all_embeddings(self):
        from ai_os.knowledge.models import EmbeddingRecord

        embeddings: list[EmbeddingRecord] = []
        docs_root = self.settings.knowledge_processed_dir / "documents"
        if not docs_root.exists():
            return embeddings
        for doc_dir in docs_root.iterdir():
            path = doc_dir / "embeddings.jsonl"
            if path.exists():
                for row in self._read_jsonl(path):
                    embeddings.append(EmbeddingRecord.model_validate(row))
        return embeddings

    def _update_manifest(self, full_rebuild: bool = False) -> None:
        registry_records = self.registry._load_all()
        doc_dirs = list((self.settings.knowledge_processed_dir / "documents").glob("*"))
        chunks = self._load_all_child_chunks()
        self.manifest.save(
            source_count=len(registry_records),
            document_count=len(doc_dirs),
            chunk_count=len(chunks),
            child_chunk_count=len(chunks),
            full_rebuild=full_rebuild,
        )
