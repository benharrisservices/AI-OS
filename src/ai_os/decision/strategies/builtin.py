"""Concrete reasoning strategy implementations."""

from __future__ import annotations

from ai_os.decision.ids import new_assumption_id, new_option_id
from ai_os.decision.models import (
    Assumption,
    Constraint,
    DecisionOption,
    DecisionRequest,
    Evidence,
    ReasoningStrategyName,
    Risk,
    RiskSeverity,
    Tradeoff,
)
from ai_os.decision.strategies import register_strategy
from ai_os.decision.strategies.base import (
    build_dimension_tradeoff,
    default_assumptions,
    default_options_from_hints,
    default_risks,
    evidence_relevance,
    extract_keywords,
    score_by_evidence_overlap,
)


class _BaseStrategy:
    tradeoff_dimensions: list[str]
    default_option_count: int = 3
    prefix: str = ""
    assumption_confidence: float = 0.6
    risk_severity: RiskSeverity = RiskSeverity.MEDIUM

    def generate_options(
        self,
        request: DecisionRequest,
        evidence: list[Evidence],
        constraints: list[Constraint],
    ) -> list[DecisionOption]:
        return default_options_from_hints(
            request, count=self.default_option_count, prefix=self.prefix
        )

    def identify_assumptions(
        self,
        request: DecisionRequest,
        evidence: list[Evidence],
    ) -> list[Assumption]:
        return default_assumptions(request, evidence, base_confidence=self.assumption_confidence)

    def compare_tradeoffs(
        self,
        options: list[DecisionOption],
        evidence: list[Evidence],
    ) -> list[Tradeoff]:
        tradeoffs: list[Tradeoff] = []
        for index, dimension in enumerate(self.tradeoff_dimensions):
            tradeoffs.append(
                build_dimension_tradeoff(dimension, options, evidence, winner_index=index % len(options))
            )
        return tradeoffs

    def evaluate_risks(
        self,
        options: list[DecisionOption],
        evidence: list[Evidence],
    ) -> list[Risk]:
        return default_risks(options, severity_bias=self.risk_severity)

    def score_options(
        self,
        options: list[DecisionOption],
        tradeoffs: list[Tradeoff],
        risks: list[Risk],
        evidence: list[Evidence],
    ) -> list[DecisionOption]:
        keywords = extract_keywords(" ".join(o.title for o in options))
        scored = score_by_evidence_overlap(options, evidence, keywords)
        for option in scored:
            win_count = sum(1 for t in tradeoffs if t.winner_option_id == option.option_id)
            risk_penalty = sum(
                r.likelihood * (0.3 if r.severity == RiskSeverity.HIGH else 0.1)
                for r in risks
                if r.option_id == option.option_id
            )
            boost = win_count * 0.08
            new_score = min(1.0, max(0.0, (option.score or 0.5) + boost - risk_penalty))
            option.score = new_score
        return sorted(scored, key=lambda o: o.score or 0, reverse=True)


class AnalyticalStrategy(_BaseStrategy):
    name = ReasoningStrategyName.ANALYTICAL
    tradeoff_dimensions = ["evidence strength", "feasibility", "cost of error"]
    prefix = "Analytically"
    assumption_confidence = 0.7
    risk_severity = RiskSeverity.MEDIUM


class StrategicStrategy(_BaseStrategy):
    name = ReasoningStrategyName.STRATEGIC
    tradeoff_dimensions = ["long-term impact", "competitive position", "resource commitment"]
    prefix = "Strategically"
    assumption_confidence = 0.55
    risk_severity = RiskSeverity.MEDIUM


class OperationalStrategy(_BaseStrategy):
    name = ReasoningStrategyName.OPERATIONAL
    tradeoff_dimensions = ["execution speed", "operational complexity", "maintenance burden"]
    prefix = "Operationally"
    default_option_count = 3
    assumption_confidence = 0.65
    risk_severity = RiskSeverity.LOW


class CreativeStrategy(_BaseStrategy):
    name = ReasoningStrategyName.CREATIVE
    tradeoff_dimensions = ["novelty", "adaptability", "stakeholder acceptance"]
    prefix = "Creatively"
    default_option_count = 4

    def generate_options(
        self,
        request: DecisionRequest,
        evidence: list[Evidence],
        constraints: list[Constraint],
    ) -> list[DecisionOption]:
        options = default_options_from_hints(
            request, count=self.default_option_count, prefix=self.prefix
        )
        options.append(
            DecisionOption(
                option_id=new_option_id(len(options) + 1),
                title="Creative alternative: reframe the problem",
                description="Challenge the premise and explore an unconventional path.",
                pros=["May uncover non-obvious solutions"],
                cons=["Higher uncertainty without precedent"],
            )
        )
        return options[: self.default_option_count]


class FirstPrinciplesStrategy(_BaseStrategy):
    name = ReasoningStrategyName.FIRST_PRINCIPLES
    tradeoff_dimensions = ["fundamental truth alignment", "dependency reduction", "reversibility"]
    prefix = "From first principles"
    assumption_confidence = 0.5

    def identify_assumptions(
        self,
        request: DecisionRequest,
        evidence: list[Evidence],
    ) -> list[Assumption]:
        assumptions = default_assumptions(request, evidence, base_confidence=0.5)
        assumptions.append(
            Assumption(
                assumption_id=new_assumption_id(len(assumptions) + 1),
                statement="Conventional approaches may embed hidden assumptions worth questioning.",
                confidence=0.6,
                rationale="First-principles reasoning requires explicit decomposition.",
            )
        )
        return assumptions


class WeightedScoringStrategy(_BaseStrategy):
    name = ReasoningStrategyName.WEIGHTED_SCORING
    tradeoff_dimensions = ["weighted impact", "weighted cost", "weighted risk"]
    prefix = "Score"
    weights = {"evidence": 0.35, "tradeoffs": 0.35, "risk": 0.30}

    def score_options(
        self,
        options: list[DecisionOption],
        tradeoffs: list[Tradeoff],
        risks: list[Risk],
        evidence: list[Evidence],
    ) -> list[DecisionOption]:
        ev_score = evidence_relevance(evidence)
        scored: list[DecisionOption] = []
        for option in options:
            wins = sum(1 for t in tradeoffs if t.winner_option_id == option.option_id)
            tradeoff_score = wins / max(len(tradeoffs), 1)
            option_risks = [r for r in risks if r.option_id == option.option_id]
            risk_score = 1.0 - (
                sum(r.likelihood for r in option_risks) / max(len(option_risks), 1)
            )
            total = (
                self.weights["evidence"] * ev_score
                + self.weights["tradeoffs"] * tradeoff_score
                + self.weights["risk"] * risk_score
            )
            scored.append(option.model_copy(update={"score": round(min(1.0, total), 4)}))
        return sorted(scored, key=lambda o: o.score or 0, reverse=True)


def register_builtin_strategies() -> None:
    for strategy in (
        AnalyticalStrategy(),
        StrategicStrategy(),
        OperationalStrategy(),
        CreativeStrategy(),
        FirstPrinciplesStrategy(),
        WeightedScoringStrategy(),
    ):
        register_strategy(strategy)
