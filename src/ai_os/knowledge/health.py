"""System health diagnostics for the Knowledge Engine."""

from __future__ import annotations

import httpx

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.integrity import IntegrityService
from ai_os.knowledge.index.keyword import KeywordIndex
from ai_os.knowledge.index.manifest import ManifestService
from ai_os.knowledge.index.vector import VectorIndex
from ai_os.knowledge.models import HealthReport, IntegrityIssue
from ai_os.knowledge.pipeline import KnowledgePipeline


def _dir_size(path) -> int:
    from pathlib import Path

    total = 0
    p = Path(path)
    if not p.exists():
        return 0
    if p.is_file():
        return p.stat().st_size
    for child in p.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


class HealthService:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.pipeline = KnowledgePipeline(settings)
        self.manifest = ManifestService(settings)
        self.vector = VectorIndex(settings)
        self.keyword = KeywordIndex(settings)
        self.integrity = IntegrityService(settings)

    def check_ollama(self) -> bool:
        try:
            url = f"{self.settings.ollama_host.rstrip('/')}/api/tags"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code != 200:
                    return False
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                target = self.settings.embedding_model
                return any(target in name for name in models)
        except Exception:
            return False

    def report(self, *, run_integrity: bool = True) -> HealthReport:
        manifest = self.manifest.load()
        chunks = self.pipeline._load_all_child_chunks()
        embeddings = self.pipeline._load_all_embeddings()
        issues: list[IntegrityIssue] = self.integrity.validate() if run_integrity else []

        storage = sum(
            _dir_size(p)
            for p in (
                self.settings.knowledge_raw_dir,
                self.settings.knowledge_processed_dir,
                self.settings.knowledge_index_dir,
            )
        )

        ollama_ok = self.check_ollama()
        warnings: list[str] = []
        recommendations: list[str] = []

        if not ollama_ok:
            warnings.append(
                f"Ollama unavailable or model '{self.settings.embedding_model}' not found"
            )
            recommendations.append(
                f"Run: ollama pull {self.settings.embedding_model}"
            )

        error_count = sum(1 for i in issues if i.severity == "error")
        warn_count = sum(1 for i in issues if i.severity == "warning")
        if error_count:
            warnings.append(f"{error_count} integrity error(s) detected")
            recommendations.append("Run: ai-os doctor --repair")
        if warn_count:
            warnings.append(f"{warn_count} integrity warning(s) detected")

        vector_count = self.vector.count()
        keyword_count = self.keyword.count()
        if vector_count != len(chunks):
            warnings.append(
                f"Vector index count ({vector_count}) differs from chunk count ({len(chunks)})"
            )
            recommendations.append("Run: ai-os maintenance reindex")

        if keyword_count != len(chunks):
            warnings.append(
                f"Keyword index count ({keyword_count}) differs from chunk count ({len(chunks)})"
            )

        if manifest.embedding_model != self.settings.embedding_model:
            warnings.append(
                "Configured embedding model differs from index manifest — re-embed required"
            )
            recommendations.append("Run: ai-os maintenance reindex")

        healthy = not warnings and not any(i.severity == "error" for i in issues)

        return HealthReport(
            healthy=healthy,
            document_count=manifest.document_count,
            chunk_count=manifest.chunk_count,
            child_chunk_count=len(chunks),
            embedding_count=len(embeddings),
            vector_index_count=vector_count,
            keyword_index_count=keyword_count,
            source_count=manifest.source_count,
            storage_bytes=storage,
            last_ingest_at=self.manifest.last_ingest_at(),
            last_reindex_at=self.manifest.last_reindex_at(),
            ollama_available=ollama_ok,
            embedding_model=self.settings.embedding_model,
            embedding_provider=self.settings.embedding_provider,
            vector_store=self.settings.vector_store,
            warnings=warnings,
            recommendations=recommendations,
            issues=issues,
        )
