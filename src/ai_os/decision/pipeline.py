"""Structured decision pipeline — reasons over ContextBundle, not raw prompts."""

from __future__ import annotations

import time

from ai_os.decision.config import DecisionSettings
from ai_os.decision.ids import (
    new_decision_id,
    new_evidence_id,
    new_recommendation_id,
)
from ai_os.decision.models import (
    ConstraintSource,
    DecisionRequest,
    DecisionResult,
    DecisionStatus,
    Evidence,
    KnowledgeSummary,
    ReasoningStep,
    Recommendation,
)
from ai_os.decision.provider import LLMProvider
from ai_os.decision.store import DecisionStore
from ai_os.decision.strategies import get_strategy
from ai_os.decision.strategies.base import (
    build_user_constraints,
    evidence_relevance,
    infer_knowledge_constraints,
)
from ai_os.decision.strategies.builtin import register_builtin_strategies
from ai_os.knowledge.models import RetrievalQuery
from ai_os.knowledge.retrieval import KnowledgeRetrieval


class DecisionPipeline:
    """Ten-stage pipeline that consumes knowledge via ContextBundle only.

    The Decision Engine never performs retrieval itself beyond calling the
    Knowledge Engine's retrieval interface. It does not embed, chunk, or index.
    """

    STAGES = (
        "understand_request",
        "retrieve_knowledge",
        "identify_assumptions",
        "identify_constraints",
        "generate_options",
        "compare_tradeoffs",
        "evaluate_risks",
        "score_confidence",
        "produce_recommendation",
        "record_reasoning_trace",
    )

    def __init__(self, settings: DecisionSettings | None = None) -> None:
        self.settings = settings or DecisionSettings()
        self.settings.ensure_dirs()
        register_builtin_strategies()
        self.retrieval = KnowledgeRetrieval()
        self.store = DecisionStore(self.settings)
        self.llm = LLMProvider(self.settings)

    def decide(self, request: DecisionRequest) -> DecisionResult:
        decision_id = new_decision_id()
        strategy = get_strategy(request.strategy)
        trace: list[ReasoningStep] = []
        evidence: list[Evidence] = []
        assumptions: list = []
        constraints: list = []
        options: list = []
        tradeoffs: list = []
        risks: list = []
        recommendation: Recommendation | None = None
        knowledge_summary: KnowledgeSummary | None = None
        confidence = 0.0
        understood: dict = {}

        try:
            # 1. Understand the request
            start = time.perf_counter()
            understood = self._understand_request(request)
            trace.append(self._step(1, "understand_request", understood, start))

            # 2. Retrieve supporting knowledge
            start = time.perf_counter()
            bundle = None
            if request.require_knowledge:
                query = request.knowledge_query or request.question
                bundle = self.retrieval.retrieve(
                    RetrievalQuery(query=query, top_k=8, retrieval_mode="context")
                )
                evidence = self._evidence_from_bundle(bundle)
                knowledge_summary = KnowledgeSummary(
                    query=bundle.query,
                    chunk_count=len(bundle.chunks),
                    citation_count=len(bundle.citations),
                    token_estimate=bundle.token_estimate,
                    search_mode=bundle.retrieval_metadata.search_mode,
                )
            trace.append(
                self._step(
                    2,
                    "retrieve_knowledge",
                    {"evidence_count": len(evidence), "query": request.knowledge_query or request.question},
                    start,
                )
            )

            # 3. Identify assumptions
            start = time.perf_counter()
            assumptions = strategy.identify_assumptions(request, evidence)
            trace.append(self._step(3, "identify_assumptions", {"count": len(assumptions)}, start))

            # 4. Identify constraints
            start = time.perf_counter()
            constraints = build_user_constraints(request)
            if evidence:
                constraints.extend(infer_knowledge_constraints(evidence))
            inferred = self._infer_constraints(request, evidence)
            constraints.extend(inferred)
            trace.append(self._step(4, "identify_constraints", {"count": len(constraints)}, start))

            # 5. Generate options
            start = time.perf_counter()
            options = strategy.generate_options(request, evidence, constraints)
            trace.append(self._step(5, "generate_options", {"count": len(options)}, start))

            # 6. Compare tradeoffs
            start = time.perf_counter()
            tradeoffs = strategy.compare_tradeoffs(options, evidence)
            trace.append(self._step(6, "compare_tradeoffs", {"count": len(tradeoffs)}, start))

            # 7. Evaluate risks
            start = time.perf_counter()
            risks = strategy.evaluate_risks(options, evidence)
            trace.append(self._step(7, "evaluate_risks", {"count": len(risks)}, start))

            # 8. Score confidence
            start = time.perf_counter()
            options = strategy.score_options(options, tradeoffs, risks, evidence)
            confidence = self._score_confidence(assumptions, evidence, options, request)
            trace.append(self._step(8, "score_confidence", {"confidence": confidence}, start))

            # 9. Produce recommendation
            start = time.perf_counter()
            recommendation = self._produce_recommendation(options, confidence, request, evidence)
            trace.append(
                self._step(
                    9,
                    "produce_recommendation",
                    {"option_id": recommendation.option_id if recommendation else None},
                    start,
                )
            )

            # 10. Record reasoning trace
            start = time.perf_counter()
            trace.append(self._step(10, "record_reasoning_trace", {"steps": len(trace) + 1}, start))

            result = DecisionResult(
                decision_id=decision_id,
                status=DecisionStatus.COMPLETED,
                request=request,
                strategy=request.strategy,
                evidence=evidence,
                assumptions=assumptions,
                constraints=constraints,
                options=options,
                tradeoffs=tradeoffs,
                risks=risks,
                recommendation=recommendation,
                confidence=confidence,
                reasoning_trace=trace,
                knowledge_summary=knowledge_summary,
                engine_version=self.settings.engine_version,
            )
            self.store.save(result)
            return result

        except Exception as exc:
            result = DecisionResult(
                decision_id=decision_id,
                status=DecisionStatus.FAILED,
                request=request,
                strategy=request.strategy,
                evidence=evidence,
                assumptions=assumptions,
                constraints=constraints,
                options=options,
                tradeoffs=tradeoffs,
                risks=risks,
                recommendation=recommendation,
                confidence=confidence,
                reasoning_trace=trace,
                knowledge_summary=knowledge_summary,
                engine_version=self.settings.engine_version,
                error=str(exc),
            )
            self.store.save(result)
            raise

    def _understand_request(self, request: DecisionRequest) -> dict:
        summary = {
            "question": request.question,
            "strategy": request.strategy.value,
            "has_context": bool(request.context),
            "constraint_count": len(request.user_constraints),
            "option_hint_count": len(request.option_hints),
        }
        if self.llm.is_available():
            enrichment = self.llm.complete(
                f"Summarize the decision question in one sentence: {request.question}"
            )
            if enrichment:
                summary["llm_summary"] = enrichment
        return summary

    def _evidence_from_bundle(self, bundle) -> list[Evidence]:
        items: list[Evidence] = []
        for index, (citation, chunk) in enumerate(
            zip(bundle.citations, bundle.chunks, strict=True), start=1
        ):
            items.append(
                Evidence(
                    evidence_id=new_evidence_id(index),
                    cite_key=citation.cite_key,
                    chunk_id=citation.chunk_id,
                    content=chunk.text[:500],
                    relevance_score=min(1.0, max(0.0, chunk.score)),
                    source_uri=citation.source_uri,
                    title=citation.title,
                )
            )
        return items

    def _infer_constraints(self, request: DecisionRequest, evidence: list[Evidence]) -> list:
        from ai_os.decision.ids import new_constraint_id
        from ai_os.decision.models import Constraint

        if not request.context:
            return []
        return [
            Constraint(
                constraint_id=new_constraint_id(200),
                description=f"Operator context: {request.context[:200]}",
                source=ConstraintSource.INFERRED,
                hard=False,
            )
        ]

    def _score_confidence(self, assumptions, evidence, options, request) -> float:
        if not options:
            return 0.0
        assumption_avg = (
            sum(a.confidence for a in assumptions) / len(assumptions) if assumptions else 0.5
        )
        ev_rel = evidence_relevance(evidence)
        top_score = options[0].score or 0.5
        penalty = 0.15 if request.require_knowledge and not evidence else 0.0
        raw = 0.3 * assumption_avg + 0.35 * ev_rel + 0.35 * top_score - penalty
        return round(min(1.0, max(0.0, raw)), 4)

    def _produce_recommendation(
        self, options, confidence: float, request: DecisionRequest, evidence: list[Evidence]
    ) -> Recommendation | None:
        if not options:
            return None
        best = options[0]
        rationale_parts = [
            f"Selected '{best.title}' with score {best.score:.2f} under {request.strategy.value} strategy.",
        ]
        if evidence:
            rationale_parts.append(f"Supported by {len(evidence)} evidence item(s).")
        else:
            rationale_parts.append("Limited evidence available; recommendation is tentative.")

        return Recommendation(
            recommendation_id=new_recommendation_id(),
            option_id=best.option_id,
            title=best.title,
            summary=best.description,
            rationale=" ".join(rationale_parts),
            confidence=confidence,
            conditions=["Revisit if new evidence contradicts assumptions"],
        )

    def _step(self, step: int, stage: str, details: dict, start: float) -> ReasoningStep:
        duration_ms = int((time.perf_counter() - start) * 1000)
        summary = f"Completed {stage}"
        if "count" in details:
            summary = f"{stage}: {details['count']} item(s)"
        if stage == "score_confidence" and "confidence" in details:
            summary = f"Overall confidence: {details['confidence']}"
        return ReasoningStep(
            step=step,
            stage=stage,
            summary=summary,
            details=details,
            duration_ms=duration_ms,
        )
