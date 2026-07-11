"""Memory System contracts — four independent memory types."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"
    PROMOTED = "promoted"


class EpisodicEventType(str, Enum):
    WORKFLOW_EXECUTION = "workflow_execution"
    CONVERSATION = "conversation"
    DECISION = "decision"
    FAILURE = "failure"
    SUCCESS = "success"
    CUSTOM = "custom"


class PromotionTarget(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class PromotionPolicy(str, Enum):
    """Policies governing memory promotion between tiers."""

    MANUAL_APPROVAL = "manual_approval"
    WORKFLOW_COMPLETION = "workflow_completion"


class MemoryRecordBase(BaseModel):
    """Shared fields across all memory types."""

    schema_version: str = "1.0"
    memory_id: str = Field(description="Unique memory identifier.")
    memory_type: MemoryType
    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkingMemory(MemoryRecordBase):
    """Short-lived execution context that automatically expires."""

    memory_type: Literal[MemoryType.WORKING] = MemoryType.WORKING
    task_id: str | None = Field(default=None, description="Owning task, if any.")
    scope: str = Field(description="Context scope, e.g. workflow or session.")
    content: dict[str, Any] = Field(
        default_factory=dict,
        description="Temporary variables and intermediate state.",
    )
    expires_at: datetime = Field(description="Automatic expiration timestamp.")


class EpisodicMemory(MemoryRecordBase):
    """Historical events searchable by time."""

    memory_type: Literal[MemoryType.EPISODIC] = MemoryType.EPISODIC
    event_type: EpisodicEventType = Field(description="Category of historical event.")
    title: str = Field(description="Short event title.")
    summary: str = Field(description="Human-readable event summary.")
    content: dict[str, Any] = Field(default_factory=dict, description="Structured event payload.")
    occurred_at: datetime = Field(default_factory=utc_now)
    source_ref: str | None = Field(
        default=None,
        description="Reference to originating task, decision, or conversation.",
    )
    archived_at: datetime | None = None


class SemanticMemory(MemoryRecordBase):
    """Learned abstractions created only through explicit promotion."""

    memory_type: Literal[MemoryType.SEMANTIC] = MemoryType.SEMANTIC
    concept: str = Field(description="Stable abstraction or preference label.")
    abstraction: str = Field(description="Distilled lesson or heuristic.")
    promoted_from: str = Field(description="Source episodic memory identifier.")
    promotion_approved: bool = Field(
        default=False,
        description="Whether promotion received explicit approval.",
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ProceduralMemory(MemoryRecordBase):
    """Version-controlled operating procedures."""

    memory_type: Literal[MemoryType.PROCEDURAL] = MemoryType.PROCEDURAL
    procedure_name: str = Field(description="Procedure identifier.")
    description: str = Field(description="What this procedure accomplishes.")
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered procedure steps or workflow template.",
    )
    version: str = Field(default="1.0.0")
    previous_version_id: str | None = Field(
        default=None,
        description="Prior procedural memory version, if any.",
    )


MemoryRecord = WorkingMemory | EpisodicMemory | SemanticMemory | ProceduralMemory


class MemorySearchQuery(BaseModel):
    """Query for retrieving memories — separate from knowledge retrieval."""

    query: str = ""
    memory_types: list[MemoryType] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    since: datetime | None = None
    until: datetime | None = None
    task_id: str | None = None
    agent_id: str | None = None
    workflow_id: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class MemoryBundle(BaseModel):
    """Relevant memories injected into Agent Runtime context."""

    working: list[WorkingMemory] = Field(default_factory=list)
    episodic: list[EpisodicMemory] = Field(default_factory=list)
    semantic: list[SemanticMemory] = Field(default_factory=list)
    procedural: list[ProceduralMemory] = Field(default_factory=list)
    summary: str = Field(default="", description="Compact context for orchestration.")

    def to_context_dict(self) -> dict[str, Any]:
        return {
            "working": [m.model_dump(mode="json") for m in self.working],
            "episodic": [m.model_dump(mode="json") for m in self.episodic],
            "semantic": [m.model_dump(mode="json") for m in self.semantic],
            "procedural": [m.model_dump(mode="json") for m in self.procedural],
            "summary": self.summary,
        }


class PromotionRequest(BaseModel):
    """Request to promote memory between tiers."""

    source_memory_id: str
    target_type: PromotionTarget
    policy: PromotionPolicy
    approved: bool = False
    approved_by: str | None = None
    concept: str | None = Field(
        default=None,
        description="Semantic concept label when promoting to semantic memory.",
    )
    abstraction: str | None = Field(
        default=None,
        description="Distilled lesson when promoting to semantic memory.",
    )


class PromotionResult(BaseModel):
    """Outcome of a promotion attempt."""

    success: bool
    source_memory_id: str
    target_memory_id: str | None = None
    target_type: PromotionTarget | None = None
    error: str | None = None
