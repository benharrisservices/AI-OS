"""Memory Manager — create, update, retrieve, archive, expire, promote."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from ai_os.memory.config import MemorySettings
from ai_os.memory.ids import new_memory_id
from ai_os.memory.models import (
    EpisodicEventType,
    EpisodicMemory,
    MemoryRecord,
    MemorySearchQuery,
    MemoryStatus,
    MemoryType,
    ProceduralMemory,
    PromotionPolicy,
    PromotionRequest,
    PromotionResult,
    PromotionTarget,
    SemanticMemory,
    WorkingMemory,
    utc_now,
)
from ai_os.memory.promotion import PromotionEngine
from ai_os.memory.retrieval import MemoryRetrieval
from ai_os.memory.store import MemoryStore


class MemoryManager:
    """Central service for all memory operations — separate from Knowledge."""

    def __init__(self, settings: MemorySettings | None = None) -> None:
        self.settings = settings or MemorySettings()
        self.settings.ensure_dirs()
        self.store = MemoryStore(self.settings)
        self.promotion = PromotionEngine(self.store)
        self.retrieval = MemoryRetrieval(self.settings)

    def create_working(
        self,
        *,
        scope: str,
        content: dict[str, Any] | None = None,
        task_id: str | None = None,
        tags: list[str] | None = None,
        ttl_minutes: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkingMemory:
        ttl = ttl_minutes or self.settings.working_ttl_minutes
        memory = WorkingMemory(
            memory_id=new_memory_id("working"),
            scope=scope,
            task_id=task_id,
            content=content or {},
            tags=tags or [],
            metadata=metadata or {},
            expires_at=utc_now() + timedelta(minutes=ttl),
        )
        self.store.save(memory)
        return memory

    def create_episodic(
        self,
        *,
        event_type: EpisodicEventType,
        title: str,
        summary: str,
        content: dict[str, Any] | None = None,
        source_ref: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EpisodicMemory:
        memory = EpisodicMemory(
            memory_id=new_memory_id("episodic"),
            event_type=event_type,
            title=title,
            summary=summary,
            content=content or {},
            source_ref=source_ref,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.store.save(memory)
        return memory

    def create_semantic(
        self,
        *,
        concept: str,
        abstraction: str,
        promoted_from: str,
        promotion_approved: bool,
        confidence: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SemanticMemory:
        if not promotion_approved:
            raise ValueError("Semantic memory requires explicit promotion approval.")
        memory = SemanticMemory(
            memory_id=new_memory_id("semantic"),
            concept=concept,
            abstraction=abstraction,
            promoted_from=promoted_from,
            promotion_approved=True,
            confidence=confidence,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.store.save(memory)
        return memory

    def create_procedural(
        self,
        *,
        procedure_name: str,
        description: str,
        steps: list[dict[str, Any]],
        version: str = "1.0.0",
        previous_version_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProceduralMemory:
        memory = ProceduralMemory(
            memory_id=new_memory_id("procedural"),
            procedure_name=procedure_name,
            description=description,
            steps=steps,
            version=version,
            previous_version_id=previous_version_id,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.store.save(memory)
        return memory

    def update(self, memory_id: str, **fields: Any) -> MemoryRecord:
        record = self.store.get(memory_id)
        if record is None:
            raise ValueError(f"Memory not found: {memory_id}")
        data = record.model_dump()
        data.update(fields)
        data["updated_at"] = utc_now()
        updated = type(record).model_validate(data)
        self.store.save(updated)
        return updated

    def get(self, memory_id: str) -> MemoryRecord | None:
        return self.store.get(memory_id)

    def search(self, query: MemorySearchQuery) -> list[MemoryRecord]:
        return self.retrieval.search(query)

    def archive(self, memory_id: str) -> MemoryRecord:
        record = self.store.get(memory_id)
        if record is None:
            raise ValueError(f"Memory not found: {memory_id}")
        record.status = MemoryStatus.ARCHIVED
        if isinstance(record, EpisodicMemory):
            record.archived_at = utc_now()
        self.store.save(record)
        return record

    def expire_working(self) -> list[str]:
        """Expire working memories past their TTL."""
        expired_ids: list[str] = []
        now = utc_now()
        for record in self.store.list_by_type(MemoryType.WORKING, status=MemoryStatus.ACTIVE):
            if not isinstance(record, WorkingMemory):
                continue
            if record.expires_at <= now:
                record.status = MemoryStatus.EXPIRED
                self.store.save(record)
                expired_ids.append(record.memory_id)
        return expired_ids

    def promote(self, request: PromotionRequest) -> PromotionResult:
        return self.promotion.promote(request)

    def promote_working_to_episodic(
        self,
        working_id: str,
        *,
        policy: PromotionPolicy = PromotionPolicy.WORKFLOW_COMPLETION,
        approved: bool = False,
        title: str | None = None,
        summary: str | None = None,
    ) -> PromotionResult:
        working = self.store.get(working_id)
        if isinstance(working, WorkingMemory):
            if title:
                working.metadata["title"] = title
            if summary:
                working.metadata["summary"] = summary
            self.store.save(working)
        return self.promote(
            PromotionRequest(
                source_memory_id=working_id,
                target_type=PromotionTarget.EPISODIC,
                policy=policy,
                approved=approved or policy == PromotionPolicy.WORKFLOW_COMPLETION,
            )
        )

    def sync_working(
        self,
        *,
        task_id: str,
        scope: str,
        content: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> WorkingMemory:
        """Create or update working memory for an active task."""
        for record in self.store.list_by_type(MemoryType.WORKING, status=MemoryStatus.ACTIVE):
            if isinstance(record, WorkingMemory) and record.task_id == task_id:
                record.content = content
                record.metadata.update(metadata or {})
                record.expires_at = utc_now() + timedelta(minutes=self.settings.working_ttl_minutes)
                self.store.save(record)
                return record
        return self.create_working(
            scope=scope,
            task_id=task_id,
            content=content,
            metadata=metadata,
        )
