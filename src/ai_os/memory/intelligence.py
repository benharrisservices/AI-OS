"""Memory intelligence — improves memory without changing architecture."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import timedelta
from typing import Any

from ai_os.memory.config import MemorySettings
from ai_os.memory.manager import MemoryManager
from ai_os.memory.models import (
    EpisodicMemory,
    MemorySearchQuery,
    MemoryStatus,
    MemoryType,
    SemanticMemory,
    utc_now,
)


class MemoryIntelligence:
    """Analyse and improve memories via MemoryManager public API only."""

    def __init__(self, settings: MemorySettings | None = None) -> None:
        self.manager = MemoryManager(settings)

    def detect_duplicates(self, *, threshold: float = 0.9) -> list[list[str]]:
        """Find potentially duplicate episodic/semantic memories by content hash."""
        groups: dict[str, list[str]] = defaultdict(list)
        for memory_type in (MemoryType.EPISODIC, MemoryType.SEMANTIC):
            for record in self.manager.list_by_type(memory_type, status=MemoryStatus.ACTIVE):
                text = self._content_text(record)
                key = hashlib.sha256(text[:500].encode()).hexdigest()[:16]
                groups[key].append(record.memory_id)
        return [ids for ids in groups.values() if len(ids) > 1]

    def cluster_semantic(self) -> dict[str, list[str]]:
        """Group semantic memories by concept prefix."""
        clusters: dict[str, list[str]] = defaultdict(list)
        for record in self.manager.list_by_type(MemoryType.SEMANTIC, status=MemoryStatus.ACTIVE):
            if isinstance(record, SemanticMemory):
                prefix = record.concept.split()[0].lower() if record.concept else "other"
                clusters[prefix].append(record.memory_id)
        return dict(clusters)

    def build_relationship_graph(self) -> dict[str, list[str]]:
        """Build memory relationship graph from promotion chains and source refs."""
        graph: dict[str, list[str]] = defaultdict(list)
        for memory_type in MemoryType:
            for record in self.manager.list_by_type(memory_type, status=None):
                if isinstance(record, SemanticMemory):
                    graph[record.memory_id].append(record.promoted_from)
                    graph[record.promoted_from].append(record.memory_id)
                if isinstance(record, EpisodicMemory) and record.source_ref:
                    graph[record.memory_id].append(record.source_ref)
        return dict(graph)

    def score_importance(self, memory_id: str) -> float:
        """Score memory importance 0-1 based on type, recency, and references."""
        record = self.manager.get(memory_id)
        if record is None:
            return 0.0
        score = 0.3
        if record.memory_type == MemoryType.SEMANTIC:
            score += 0.4
        elif record.memory_type == MemoryType.EPISODIC:
            score += 0.2
        age_days = (utc_now() - record.created_at).days
        score += max(0, 0.3 - age_days * 0.01)
        if isinstance(record, SemanticMemory):
            score += record.confidence * 0.2
        return min(1.0, score)

    def score_confidence(self, memory_id: str) -> float:
        record = self.manager.get(memory_id)
        if record is None:
            return 0.0
        if isinstance(record, SemanticMemory):
            return record.confidence
        if isinstance(record, EpisodicMemory):
            return 0.6
        return 0.4

    def apply_aging(self, *, max_age_days: int = 90) -> list[str]:
        """Archive episodic memories older than max_age_days."""
        cutoff = utc_now() - timedelta(days=max_age_days)
        archived: list[str] = []
        for record in self.manager.list_by_type(MemoryType.EPISODIC, status=MemoryStatus.ACTIVE):
            if isinstance(record, EpisodicMemory) and record.occurred_at < cutoff:
                self.manager.archive(record.memory_id)
                archived.append(record.memory_id)
        return archived

    def forgetting_policy(self, *, min_importance: float = 0.2) -> list[str]:
        """Archive low-importance active memories."""
        forgotten: list[str] = []
        for memory_type in (MemoryType.EPISODIC, MemoryType.WORKING):
            for record in self.manager.list_by_type(memory_type, status=MemoryStatus.ACTIVE):
                if self.score_importance(record.memory_id) < min_importance:
                    self.manager.archive(record.memory_id)
                    forgotten.append(record.memory_id)
        return forgotten

    def detect_contradictions(self) -> list[dict[str, Any]]:
        """Find semantic memories with conflicting concepts."""
        semantics = [
            r for r in self.manager.list_by_type(MemoryType.SEMANTIC, status=MemoryStatus.ACTIVE)
            if isinstance(r, SemanticMemory)
        ]
        contradictions: list[dict[str, Any]] = []
        for i, a in enumerate(semantics):
            for b in semantics[i + 1:]:
                if a.concept.lower() == b.concept.lower() and a.abstraction != b.abstraction:
                    contradictions.append({
                        "concept": a.concept,
                        "memory_a": a.memory_id,
                        "memory_b": b.memory_id,
                    })
        return contradictions

    def build_timeline(self, *, query: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Reconstruct chronological timeline of episodic memories."""
        records = self.manager.search(MemorySearchQuery(
            query=query,
            memory_types=[MemoryType.EPISODIC],
            limit=limit,
        ))
        timeline: list[dict[str, Any]] = []
        for record in records:
            if isinstance(record, EpisodicMemory):
                timeline.append({
                    "memory_id": record.memory_id,
                    "occurred_at": record.occurred_at.isoformat(),
                    "event_type": record.event_type.value,
                    "title": record.title,
                    "summary": record.summary,
                })
        return sorted(timeline, key=lambda e: e["occurred_at"])

    def compress_episodic(self, *, limit: int = 20) -> dict[str, Any]:
        """Compress recent episodic memories into a summary digest."""
        records = self.manager.list_by_type(MemoryType.EPISODIC, status=MemoryStatus.ACTIVE)[:limit]
        summaries = [r.summary for r in records if isinstance(r, EpisodicMemory)]
        return {
            "count": len(summaries),
            "digest": "\n".join(f"- {s}" for s in summaries[:10]),
        }

    def promotion_recommendations(self) -> list[dict[str, Any]]:
        """Recommend episodic memories for semantic promotion."""
        recommendations: list[dict[str, Any]] = []
        for record in self.manager.list_by_type(MemoryType.EPISODIC, status=MemoryStatus.ACTIVE):
            if not isinstance(record, EpisodicMemory):
                continue
            importance = self.score_importance(record.memory_id)
            if importance >= 0.6:
                recommendations.append({
                    "memory_id": record.memory_id,
                    "title": record.title,
                    "importance": round(importance, 2),
                    "reason": "High importance episodic memory",
                })
        return sorted(recommendations, key=lambda r: r["importance"], reverse=True)

    def _content_text(self, record) -> str:
        parts = []
        for attr in ("summary", "abstraction", "title", "concept"):
            if v := getattr(record, attr, None):
                parts.append(str(v))
        return " ".join(parts)

    def _text(self, record) -> str:
        return f"{record.memory_id} {self._content_text(record)}"
