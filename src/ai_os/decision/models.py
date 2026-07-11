"""Decision Engine contracts — provider-agnostic, strongly typed."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReasoningStrategyName(str, Enum):
    ANALYTICAL = "analytical"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    CREATIVE = "creative"
    FIRST_PRINCIPLES = "first_principles"
    WEIGHTED_SCORING = "weighted_scoring"


class DecisionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConstraintSource(str, Enum):
    USER = "user"
    KNOWLEDGE = "knowledge"
    INFERRED = "inferred"


class DecisionRequest(BaseModel):
    """Input to the decision pipeline.

    The Decision Engine reasons over a question. Knowledge retrieval is
  delegated to the Knowledge Engine via ``knowledge_query``.
    """

    question: str = Field(description="The decision question to reason about.")
    strategy: ReasoningStrategyName = Field(
        default=ReasoningStrategyName.ANALYTICAL,
        description="Reasoning mode that shapes how options and tradeoffs are evaluated.",
    )
    context: str | None = Field(
        default=None,
        description="Optional operator-supplied background not present in the knowledge base.",
    )
    knowledge_query: str | None = Field(
        default=None,
        description="Query sent to the Knowledge Engine; defaults to ``question`` when omitted.",
    )
    user_constraints: list[str] = Field(
        default_factory=list,
        description="Hard or soft constraints supplied by the operator.",
    )
    option_hints: list[str] = Field(
        default_factory=list,
        description="Optional candidate options suggested by the operator.",
    )
    require_knowledge: bool = Field(
        default=True,
        description="When true, the pipeline retrieves evidence before reasoning.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Opaque key-value metadata for logging and future integrations.",
    )


class DecisionOption(BaseModel):
    """A viable course of action under consideration."""

    option_id: str = Field(description="Stable identifier for this option within the decision.")
    title: str = Field(description="Short label for the option.")
    description: str = Field(description="What this option entails in practice.")
    pros: list[str] = Field(default_factory=list, description="Advantages of this option.")
    cons: list[str] = Field(default_factory=list, description="Disadvantages of this option.")
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Normalized score after strategy-specific evaluation; higher is better.",
    )


class Evidence(BaseModel):
    """A piece of supporting information retrieved from the Knowledge Engine."""

    evidence_id: str = Field(description="Stable identifier within this decision.")
    cite_key: str = Field(description="Citation marker from the knowledge bundle, e.g. [1].")
    chunk_id: str | None = Field(default=None, description="Source chunk ID from the Knowledge Engine.")
    content: str = Field(description="Excerpt or passage used as evidence.")
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How relevant this evidence is to the decision question.",
    )
    source_uri: str = Field(description="URI of the original source document.")
    title: str = Field(default="", description="Title of the source document.")


class Assumption(BaseModel):
    """A belief taken as true without direct evidence in the retrieved context."""

    assumption_id: str = Field(description="Stable identifier within this decision.")
    statement: str = Field(description="The assumption being made.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence that the assumption holds (1.0 = certain).",
    )
    rationale: str = Field(description="Why this assumption is reasonable or necessary.")


class Constraint(BaseModel):
    """A boundary or requirement that limits viable options."""

    constraint_id: str = Field(description="Stable identifier within this decision.")
    description: str = Field(description="What must be respected.")
    source: ConstraintSource = Field(description="Where the constraint originated.")
    hard: bool = Field(
        default=True,
        description="Hard constraints eliminate non-compliant options; soft constraints penalize them.",
    )


class Risk(BaseModel):
    """A potential negative outcome associated with an option."""

    risk_id: str = Field(description="Stable identifier within this decision.")
    description: str = Field(description="What could go wrong.")
    severity: RiskSeverity = Field(description="Impact if the risk materializes.")
    likelihood: float = Field(
        ge=0.0,
        le=1.0,
        description="Estimated probability the risk occurs.",
    )
    option_id: str | None = Field(default=None, description="Option this risk is tied to, if specific.")
    mitigation: str | None = Field(default=None, description="Suggested way to reduce the risk.")


class Tradeoff(BaseModel):
    """A comparison dimension across two or more options."""

    tradeoff_id: str = Field(description="Stable identifier within this decision.")
    dimension: str = Field(description="What is being compared, e.g. cost, speed, risk.")
    option_ids: list[str] = Field(description="Options evaluated on this dimension.")
    analysis: str = Field(description="Narrative comparison across options.")
    winner_option_id: str | None = Field(
        default=None,
        description="Option that fares best on this dimension, if determinable.",
    )


class Recommendation(BaseModel):
    """The pipeline's recommended course of action."""

    recommendation_id: str = Field(description="Stable identifier for this recommendation.")
    option_id: str = Field(description="ID of the recommended option.")
    title: str = Field(description="Short label for the recommendation.")
    summary: str = Field(description="One-paragraph recommendation for the operator.")
    rationale: str = Field(description="Why this option was chosen over alternatives.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the recommendation given available evidence.",
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions under which the recommendation should be revisited.",
    )


class ReasoningStep(BaseModel):
    """A single stage in the decision pipeline trace."""

    step: int = Field(description="Pipeline stage number (1–10).")
    stage: str = Field(description="Stage name, e.g. retrieve_knowledge.")
    summary: str = Field(description="Human-readable summary of what happened.")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured stage output.")
    duration_ms: int = Field(default=0, description="Wall-clock time for this stage.")


class OutcomeRecord(BaseModel):
    """Future outcome tracking — populated after the decision is acted upon."""

    recorded_at: datetime | None = Field(default=None, description="When the outcome was recorded.")
    actual_choice: str | None = Field(default=None, description="What was actually decided.")
    result_summary: str | None = Field(default=None, description="What happened after the decision.")
    success: bool | None = Field(default=None, description="Whether the outcome met expectations.")


class KnowledgeSummary(BaseModel):
    """Lightweight reference to retrieved knowledge — not the full bundle."""

    query: str
    chunk_count: int = 0
    citation_count: int = 0
    token_estimate: int = 0
    search_mode: str = "hybrid"


class DecisionResult(BaseModel):
    """Complete output of a decision pipeline run."""

    schema_version: str = "1.0"
    engine_version: str = "1.0.0"
    decision_id: str = Field(description="Unique identifier for this decision run.")
    status: DecisionStatus = Field(description="Whether the pipeline completed successfully.")
    request: DecisionRequest = Field(description="Original request.")
    strategy: ReasoningStrategyName = Field(description="Strategy used for reasoning.")
    evidence: list[Evidence] = Field(default_factory=list, description="Retrieved supporting evidence.")
    assumptions: list[Assumption] = Field(default_factory=list, description="Assumptions made during reasoning.")
    constraints: list[Constraint] = Field(default_factory=list, description="Constraints applied.")
    options: list[DecisionOption] = Field(default_factory=list, description="Options considered.")
    tradeoffs: list[Tradeoff] = Field(default_factory=list, description="Tradeoff analyses across options.")
    risks: list[Risk] = Field(default_factory=list, description="Identified risks.")
    recommendation: Recommendation | None = Field(default=None, description="Final recommendation, if any.")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the decision output.",
    )
    reasoning_trace: list[ReasoningStep] = Field(
        default_factory=list,
        description="Ordered trace of all pipeline stages.",
    )
    knowledge_summary: KnowledgeSummary | None = Field(
        default=None,
        description="Summary of knowledge retrieved; full bundle is not persisted.",
    )
    created_at: datetime = Field(default_factory=utc_now, description="When the decision was produced.")
    outcome: OutcomeRecord | None = Field(
        default=None,
        description="Future field for post-decision outcome tracking.",
    )
    error: str | None = Field(default=None, description="Error message when status is failed.")
