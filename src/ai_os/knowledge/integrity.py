"""Index integrity validation and repair."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.embedding import EmbeddingService
from ai_os.knowledge.index.keyword import KeywordIndex
from ai_os.knowledge.index.manifest import ManifestService
from ai_os.knowledge.index.vector import VectorIndex
from ai_os.knowledge.io import read_json, read_jsonl
from ai_os.knowledge.models import ChunkRecord, EmbeddingRecord, IntegrityIssue, SourceStatus
from ai_os.knowledge.pipeline import KnowledgePipeline
from ai_os.knowledge.registry import SourceRegistry


class IntegrityService:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.registry = SourceRegistry(settings)
        self.vector = VectorIndex(settings)
        self.keyword = KeywordIndex(settings)
        self.manifest = ManifestService(settings)
        self.embedder = EmbeddingService(settings)

    def validate(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        issues.extend(self._check_registry_vs_raw())
        issues.extend(self._check_processed_documents())
        issues.extend(self._check_chunk_embedding_alignment())
        issues.extend(self._check_vector_index())
        issues.extend(self._check_keyword_index())
        issues.extend(self._check_manifest())
        issues.extend(self._check_orphaned_cache())
        issues.extend(self._check_duplicate_chunk_ids())
        return issues

    def repair(self, issues: list[IntegrityIssue] | None = None) -> list[str]:
        found = issues if issues is not None else self.validate()
        actions: list[str] = []
        repairable = [i for i in found if i.repairable]

        stale_vector = [i for i in repairable if i.code == "STALE_VECTOR_ENTRY"]
        if stale_vector:
            ids = [i.resource_id for i in stale_vector if i.resource_id]
            self.vector.delete_chunks([cid for cid in ids if cid])
            actions.append(f"Removed {len(ids)} stale vector entries")

        stale_keyword = [i for i in repairable if i.code == "STALE_KEYWORD_ENTRY"]
        if stale_keyword:
            ids = [i.resource_id for i in stale_keyword if i.resource_id]
            self.keyword.delete_chunks([cid for cid in ids if cid])
            actions.append(f"Removed {len(ids)} stale keyword entries")

        orphan_cache = [i for i in repairable if i.code == "ORPHANED_CACHE"]
        if orphan_cache:
            hashes = [i.resource_id for i in orphan_cache if i.resource_id]
            removed = self.embedder.purge_cache_hashes([h for h in hashes if h])
            actions.append(f"Purged {removed} orphaned cache files")

        if any(i.code == "MANIFEST_MISMATCH" for i in repairable):
            pipeline = KnowledgePipeline(self.settings)
            pipeline._update_manifest()
            actions.append("Refreshed index manifest counts")

        if any(i.code in {"MISSING_EMBEDDINGS", "VECTOR_INDEX_MISMATCH"} for i in repairable):
            pipeline = KnowledgePipeline(self.settings)
            pipeline.reindex_all()
            actions.append("Rebuilt vector and keyword indexes from processed artifacts")

        tombstoned_dirs = [i for i in repairable if i.code == "ORPHAN_PROCESSED_DOC"]
        for issue in tombstoned_dirs:
            if issue.resource_id:
                doc_dir = self.settings.knowledge_processed_dir / "documents" / issue.resource_id
                if doc_dir.exists():
                    import shutil

                    shutil.rmtree(doc_dir)
                    actions.append(f"Removed orphan processed doc {issue.resource_id}")

        return actions

    def _check_registry_vs_raw(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        for record in self.registry._load_all():
            raw_dir = self.settings.knowledge_raw_dir / record.source_id
            if record.status != SourceStatus.TOMBSTONED and not raw_dir.exists():
                issues.append(
                    IntegrityIssue(
                        severity="error",
                        code="MISSING_RAW",
                        message=f"Registry source {record.source_id} has no raw directory",
                        resource_id=record.source_id,
                        repairable=False,
                    )
                )
        return issues

    def _check_processed_documents(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        known_doc_ids = {
            doc_id for r in self.registry._load_all() for doc_id in r.doc_ids if r.status != SourceStatus.TOMBSTONED
        }
        docs_root = self.settings.knowledge_processed_dir / "documents"
        if not docs_root.exists():
            return issues

        for doc_dir in docs_root.iterdir():
            if not doc_dir.is_dir():
                continue
            doc_id = doc_dir.name
            if doc_id not in known_doc_ids:
                issues.append(
                    IntegrityIssue(
                        severity="warning",
                        code="ORPHAN_PROCESSED_DOC",
                        message=f"Processed document {doc_id} not referenced by any active source",
                        resource_id=doc_id,
                        repairable=True,
                    )
                )
            for required in ("document.meta.json", "chunks.jsonl", "embeddings.jsonl"):
                if not (doc_dir / required).exists():
                    issues.append(
                        IntegrityIssue(
                            severity="error",
                            code="MISSING_ARTIFACT",
                            message=f"Document {doc_id} missing {required}",
                            resource_id=doc_id,
                            repairable=False,
                        )
                    )
        return issues

    def _check_chunk_embedding_alignment(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        docs_root = self.settings.knowledge_processed_dir / "documents"
        if not docs_root.exists():
            return issues

        for doc_dir in docs_root.iterdir():
            if not doc_dir.is_dir():
                continue
            chunks = [
                ChunkRecord.model_validate(row)
                for row in read_jsonl(doc_dir / "chunks.jsonl")
            ]
            embeddings = [
                EmbeddingRecord.model_validate(row)
                for row in read_jsonl(doc_dir / "embeddings.jsonl")
            ]
            child_ids = {c.chunk_id for c in chunks if c.chunk_level.value == "child"}
            embed_ids = {e.chunk_id for e in embeddings}
            missing = child_ids - embed_ids
            if missing:
                issues.append(
                    IntegrityIssue(
                        severity="error",
                        code="MISSING_EMBEDDINGS",
                        message=f"Document {doc_dir.name} missing embeddings for {len(missing)} chunk(s)",
                        resource_id=doc_dir.name,
                        repairable=True,
                    )
                )
        return issues

    def _check_vector_index(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        expected = {c.chunk_id for c in self._all_child_chunks()}
        actual = set(self.vector.list_ids())
        stale = actual - expected
        missing = expected - actual

        for chunk_id in stale:
            issues.append(
                IntegrityIssue(
                    severity="warning",
                    code="STALE_VECTOR_ENTRY",
                    message=f"Vector index contains chunk not in processed store: {chunk_id}",
                    resource_id=chunk_id,
                    repairable=True,
                )
            )
        if missing:
            issues.append(
                IntegrityIssue(
                    severity="error",
                    code="VECTOR_INDEX_MISMATCH",
                    message=f"Vector index missing {len(missing)} chunk(s)",
                    repairable=True,
                )
            )
        return issues

    def _check_keyword_index(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        expected = {c.chunk_id for c in self._all_child_chunks()}
        actual = set(self.keyword.list_ids())
        stale = actual - expected
        missing = expected - actual

        for chunk_id in stale:
            issues.append(
                IntegrityIssue(
                    severity="warning",
                    code="STALE_KEYWORD_ENTRY",
                    message=f"Keyword index contains chunk not in processed store: {chunk_id}",
                    resource_id=chunk_id,
                    repairable=True,
                )
            )
        if missing:
            issues.append(
                IntegrityIssue(
                    severity="warning",
                    code="KEYWORD_INDEX_MISMATCH",
                    message=f"Keyword index missing {len(missing)} chunk(s)",
                    repairable=True,
                )
            )
        return issues

    def _check_manifest(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        manifest = self.manifest.load()
        docs = list((self.settings.knowledge_processed_dir / "documents").glob("*"))
        doc_dirs = [d for d in docs if d.is_dir()]
        chunks = self._all_child_chunks()
        embeddings = self._all_embeddings()

        if manifest.document_count != len(doc_dirs):
            issues.append(
                IntegrityIssue(
                    severity="warning",
                    code="MANIFEST_MISMATCH",
                    message="Manifest document_count does not match processed documents",
                    repairable=True,
                )
            )
        if manifest.child_chunk_count != len(chunks):
            issues.append(
                IntegrityIssue(
                    severity="warning",
                    code="MANIFEST_MISMATCH",
                    message="Manifest chunk_count does not match processed chunks",
                    repairable=True,
                )
            )
        if manifest.embedding_count and manifest.embedding_count != len(embeddings):
            issues.append(
                IntegrityIssue(
                    severity="warning",
                    code="MANIFEST_MISMATCH",
                    message="Manifest embedding_count does not match embeddings.jsonl files",
                    repairable=True,
                )
            )
        return issues

    def _check_orphaned_cache(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        known_hashes = {c.content_hash for c in self._all_child_chunks()}
        cache_dir = self.settings.knowledge_index_dir / "embeddings" / "cache"
        if not cache_dir.exists():
            return issues

        for path in cache_dir.glob("*.json"):
            content_hash = path.stem.replace("_", ":", 1)
            if content_hash.startswith("query:"):
                continue
            if content_hash not in known_hashes:
                issues.append(
                    IntegrityIssue(
                        severity="info",
                        code="ORPHANED_CACHE",
                        message=f"Embedding cache file has no matching chunk: {path.name}",
                        resource_id=content_hash,
                        repairable=True,
                    )
                )
        return issues

    def _check_duplicate_chunk_ids(self) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        all_ids: list[str] = []
        docs_root = self.settings.knowledge_processed_dir / "documents"
        if not docs_root.exists():
            return issues
        for doc_dir in docs_root.iterdir():
            if not doc_dir.is_dir():
                continue
            for row in read_jsonl(doc_dir / "chunks.jsonl"):
                all_ids.append(row["chunk_id"])
        counts = Counter(all_ids)
        for chunk_id, count in counts.items():
            if count > 1:
                issues.append(
                    IntegrityIssue(
                        severity="error",
                        code="DUPLICATE_CHUNK_ID",
                        message=f"Chunk ID {chunk_id} appears {count} times across documents",
                        resource_id=chunk_id,
                        repairable=False,
                    )
                )
        return issues

    def _all_child_chunks(self) -> list[ChunkRecord]:
        pipeline = KnowledgePipeline(self.settings)
        return pipeline._load_all_child_chunks()

    def _all_embeddings(self) -> list[EmbeddingRecord]:
        pipeline = KnowledgePipeline(self.settings)
        return pipeline._load_all_embeddings()
