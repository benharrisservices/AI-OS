"""Shared strategy helpers."""

from __future__ import annotations

import re

from ai_os.decision.ids import (
    new_assumption_id,
    new_constraint_id,
    new_option_id,
    new_risk_id,
    new_tradeoff_id,
)
from ai_os.decision.models import (
    Assumption,
    Constraint,
    ConstraintSource,
    DecisionOption,
    DecisionRequest,
    Evidence,
    Risk,
    RiskSeverity,
    Tradeoff,
)


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    stop = {"should", "would", "could", "which", "what", "when", "where", "there", "their", "about"}
    return [w for w in words if w not in stop][:12]


def evidence_relevance(evidence: list[Evidence]) -> float:
    if not evidence:
        return 0.0
    return sum(e.relevance_score for e in evidence) / len(evidence)


def build_user_constraints(request: DecisionRequest) -> list[Constraint]:
    return [
        Constraint(
            constraint_id=new_constraint_id(index),
            description=text,
            source=ConstraintSource.USER,
            hard=True,
        )
        for index, text in enumerate(request.user_constraints, start=1)
    ]


def infer_knowledge_constraints(evidence: list[Evidence]) -> list[Constraint]:
    constraints: list[Constraint] = []
    for index, item in enumerate(evidence[:3], start=1):
        constraints.append(
            Constraint(
                constraint_id=new_constraint_id(100 + index),
                description=f"Align with documented knowledge: {item.title or item.cite_key}",
                source=ConstraintSource.KNOWLEDGE,
                hard=False,
            )
        )
    return constraints


def default_options_from_hints(
    request: DecisionRequest,
    *,
    count: int,
    prefix: str,
) -> list[DecisionOption]:
    if request.option_hints:
        return [
            DecisionOption(
                option_id=new_option_id(index),
                title=hint[:80],
                description=f"Pursue the approach: {hint}",
                pros=[f"Directly addresses: {hint}"],
                cons=["Requires further validation against constraints"],
            )
            for index, hint in enumerate(request.option_hints[:count], start=1)
        ]

    keywords = extract_keywords(request.question)
    topic = keywords[0] if keywords else "the question"
    templates = [
        (f"{prefix} proceed with {topic}", f"Take action aligned with {topic} based on available evidence."),
        (f"{prefix} defer decision", f"Gather more evidence before committing on {topic}."),
        (f"{prefix} hybrid approach", f"Combine incremental steps with a staged plan for {topic}."),
    ]
    return [
        DecisionOption(
            option_id=new_option_id(index),
            title=title,
            description=desc,
            pros=["Structured path forward"],
            cons=["May not capture all edge cases"],
        )
        for index, (title, desc) in enumerate(templates[:count], start=1)
    ]


def default_assumptions(request: DecisionRequest, evidence: list[Evidence], *, base_confidence: float) -> list[Assumption]:
    assumptions = [
        Assumption(
            assumption_id=new_assumption_id(1),
            statement="Available evidence is representative of the decision context.",
            confidence=base_confidence,
            rationale="Derived from retrieved knowledge bundle scope.",
        ),
        Assumption(
            assumption_id=new_assumption_id(2),
            statement="No critical information is missing from the knowledge base.",
            confidence=max(0.3, base_confidence - 0.2),
            rationale="Absence of evidence cannot prove completeness.",
        ),
    ]
    if not evidence:
        assumptions.append(
            Assumption(
                assumption_id=new_assumption_id(3),
                statement="General reasoning without domain-specific evidence is sufficient.",
                confidence=0.4,
                rationale="No knowledge chunks were retrieved for this question.",
            )
        )
    return assumptions


def default_risks(options: list[DecisionOption], *, severity_bias: RiskSeverity) -> list[Risk]:
    risks: list[Risk] = []
    for index, option in enumerate(options, start=1):
        risks.append(
            Risk(
                risk_id=new_risk_id(index),
                description=f"Unforeseen factors may reduce effectiveness of '{option.title}'.",
                severity=severity_bias,
                likelihood=0.35,
                option_id=option.option_id,
                mitigation="Define success metrics and review points before committing.",
            )
        )
    return risks


def score_by_evidence_overlap(
    options: list[DecisionOption],
    evidence: list[Evidence],
    keywords: list[str],
) -> list[DecisionOption]:
    if not options:
        return options
    scored: list[DecisionOption] = []
    for option in options:
        text = f"{option.title} {option.description}".lower()
        overlap = sum(1 for kw in keywords if kw in text)
        evidence_boost = evidence_relevance(evidence) * 0.3
        base = 0.4 + (overlap / max(len(keywords), 1)) * 0.3 + evidence_boost
        scored.append(option.model_copy(update={"score": min(1.0, base)}))
    return scored


def build_dimension_tradeoff(
    dimension: str,
    options: list[DecisionOption],
    evidence: list[Evidence],
    *,
    winner_index: int = 0,
) -> Tradeoff:
    analysis_parts = []
    for option in options:
        analysis_parts.append(f"{option.title}: evaluated on {dimension}.")
    if evidence:
        analysis_parts.append(f"Evidence from {len(evidence)} source(s) informs this comparison.")
    winner = options[winner_index].option_id if options else None
    return Tradeoff(
        tradeoff_id=new_tradeoff_id(hash(dimension) % 1000),
        dimension=dimension,
        option_ids=[o.option_id for o in options],
        analysis=" ".join(analysis_parts),
        winner_option_id=winner,
    )
