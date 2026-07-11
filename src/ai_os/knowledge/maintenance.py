"""Scheduled maintenance tasks for the Knowledge Engine."""

from __future__ import annotations

import tarfile
from datetime import datetime, timezone
from pathlib import Path

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.embedding import EmbeddingService
from ai_os.knowledge.integrity import IntegrityService
from ai_os.knowledge.pipeline import KnowledgePipeline
from ai_os.knowledge.purge import PurgeService
from ai_os.knowledge.watcher import InboxWatcher


class MaintenanceService:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.pipeline = KnowledgePipeline(settings)
        self.integrity = IntegrityService(settings)
        self.embedder = EmbeddingService(settings)
        self.purge = PurgeService(settings)

    def ingest_inbox(self) -> int:
        watcher = InboxWatcher(self.settings)
        return watcher.run_once()

    def reindex(self) -> None:
        self.pipeline.reindex_all()

    def cleanup(self) -> list[str]:
        actions: list[str] = []
        issues = self.integrity.validate()
        repairable = [i for i in issues if i.repairable]
        actions.extend(self.integrity.repair(repairable))

        cache_dir = self.settings.knowledge_index_dir / "embeddings" / "cache"
        known_hashes = {c.content_hash for c in self.pipeline._load_all_child_chunks()}
        if cache_dir.exists():
            removed = 0
            for path in cache_dir.glob("*.json"):
                content_hash = path.stem.replace("_", ":", 1)
                if content_hash.startswith("query:"):
                    continue
                if content_hash not in known_hashes:
                    path.unlink()
                    removed += 1
            if removed:
                actions.append(f"Purged {removed} orphaned embedding cache files")

        catalog = self.settings.knowledge_processed_dir / ".catalog" / "documents.jsonl"
        if catalog.exists():
            catalog.unlink()
            actions.append("Cleared stale document catalog (will rebuild on next ingest)")

        return actions

    def doctor(self, *, repair: bool = False) -> tuple[list, list[str]]:
        issues = self.integrity.validate()
        actions: list[str] = []
        if repair:
            actions = self.integrity.repair(issues)
        return issues, actions

    def backup(self, destination: Path | None = None) -> Path:
        self.settings.knowledge_backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if destination is None:
            destination = self.settings.knowledge_backup_dir / f"knowledge-backup-{timestamp}.tar.gz"
        destination = destination.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        with tarfile.open(destination, "w:gz") as archive:
            for label, root in (
                ("raw", self.settings.knowledge_raw_dir),
                ("processed", self.settings.knowledge_processed_dir),
                ("index", self.settings.knowledge_index_dir),
            ):
                if root.exists():
                    archive.add(root, arcname=f"knowledge/{label}")

        return destination

    def run_all(self) -> dict[str, object]:
        """Run the full maintenance cycle: ingest, doctor, cleanup, reindex if needed."""
        results: dict[str, object] = {}
        results["ingested"] = self.ingest_inbox()
        issues, repair_actions = self.doctor(repair=True)
        results["issues_found"] = len(issues)
        results["repair_actions"] = repair_actions
        cleanup_actions = self.cleanup()
        results["cleanup_actions"] = cleanup_actions

        from ai_os.knowledge.health import HealthService

        health = HealthService(self.settings).report(run_integrity=False)
        if health.vector_index_count != health.child_chunk_count:
            self.reindex()
            results["reindexed"] = True
        else:
            results["reindexed"] = False

        return results
