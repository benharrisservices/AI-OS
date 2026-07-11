"""Promotion rules — staged transitions only, never bypassed."""

from __future__ import annotations

from ai_os.memory.models import (
    EpisodicEventType,
    EpisodicMemory,
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    PromotionPolicy,
    PromotionRequest,
    PromotionResult,
    PromotionTarget,
    SemanticMemory,
    WorkingMemory,
)
from ai_os.memory.store import MemoryStore


class PromotionError(Exception):
    pass


_ALLOWED_TRANSITIONS: dict[MemoryType, set[PromotionTarget]] = {
    MemoryType.WORKING: {PromotionTarget.EPISODIC},
    MemoryType.EPISODIC: {PromotionTarget.SEMANTIC},
}


class PromotionEngine:
    """Enforces staged promotion: Working → Episodic → Semantic."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def promote(self, request: PromotionRequest) -> PromotionResult:
        source = self.store.get(request.source_memory_id)
        if source is None:
            return PromotionResult(
                success=False,
                source_memory_id=request.source_memory_id,
                error=f"Memory not found: {request.source_memory_id}",
            )

        try:
            self._validate_transition(source, request)
            target = self._create_target(source, request)
        except PromotionError as exc:
            return PromotionResult(
                success=False,
                source_memory_id=request.source_memory_id,
                error=str(exc),
            )

        self.store.save(target)
        source.status = MemoryStatus.PROMOTED
        self.store.save(source)

        return PromotionResult(
            success=True,
            source_memory_id=request.source_memory_id,
            target_memory_id=target.memory_id,
            target_type=request.target_type,
        )

    def _validate_transition(self, source: MemoryRecord, request: PromotionRequest) -> None:
        if source.status not in (MemoryStatus.ACTIVE, MemoryStatus.EXPIRED):
            raise PromotionError(f"Cannot promote memory with status: {source.status.value}")

        allowed = _ALLOWED_TRANSITIONS.get(source.memory_type, set())
        if request.target_type not in allowed:
            raise PromotionError(
                f"Invalid promotion: {source.memory_type.value} → {request.target_type.value}. "
                "Stages cannot be bypassed."
            )

        if request.target_type == PromotionTarget.SEMANTIC:
            if request.policy != PromotionPolicy.MANUAL_APPROVAL:
                raise PromotionError("Semantic promotion requires manual_approval policy.")
            if not request.approved:
                raise PromotionError("Semantic promotion requires explicit user approval.")

        if request.target_type == PromotionTarget.EPISODIC:
            if request.policy == PromotionPolicy.MANUAL_APPROVAL and not request.approved:
                raise PromotionError("Episodic promotion via manual_approval requires --approve.")
            if request.policy not in (
                PromotionPolicy.MANUAL_APPROVAL,
                PromotionPolicy.WORKFLOW_COMPLETION,
            ):
                raise PromotionError(f"Unsupported promotion policy: {request.policy.value}")

    def _create_target(self, source: MemoryRecord, request: PromotionRequest) -> MemoryRecord:
        from ai_os.memory.ids import new_memory_id

        if request.target_type == PromotionTarget.EPISODIC:
            if not isinstance(source, WorkingMemory):
                raise PromotionError("Only working memory can promote to episodic.")
            return EpisodicMemory(
                memory_id=new_memory_id("episodic"),
                event_type=EpisodicEventType.WORKFLOW_EXECUTION,
                title=source.metadata.get("title", f"Promoted from {source.memory_id}"),
                summary=source.metadata.get("summary", "Working memory promoted to episodic."),
                content=dict(source.content),
                occurred_at=source.created_at,
                source_ref=source.task_id,
                tags=list(source.tags),
                metadata={
                    "promoted_from": source.memory_id,
                    "policy": request.policy.value,
                },
            )

        if request.target_type == PromotionTarget.SEMANTIC:
            if not isinstance(source, EpisodicMemory):
                raise PromotionError("Only episodic memory can promote to semantic.")
            concept = request.concept or source.title
            abstraction = request.abstraction or source.summary
            return SemanticMemory(
                memory_id=new_memory_id("semantic"),
                concept=concept,
                abstraction=abstraction,
                promoted_from=source.memory_id,
                promotion_approved=True,
                confidence=0.7,
                tags=list(source.tags),
                metadata={
                    "promoted_from": source.memory_id,
                    "policy": request.policy.value,
                    "approved_by": request.approved_by,
                },
            )

        raise PromotionError(f"Unsupported target type: {request.target_type}")
