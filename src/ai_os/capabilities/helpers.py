"""Shared skill helpers — compose existing engines only."""

from __future__ import annotations

from typing import Any

from ai_os.decision.models import DecisionRequest, ReasoningStrategyName
from ai_os.decision.pipeline import DecisionPipeline
from ai_os.knowledge.models import RetrievalQuery
from ai_os.knowledge.retrieval import KnowledgeRetrieval, format_context_prompt
from ai_os.memory.manager import MemoryManager
from ai_os.memory.models import MemorySearchQuery


def retrieve_knowledge(query: str, *, top_k: int = 10) -> dict[str, Any]:
    bundle = KnowledgeRetrieval().retrieve(RetrievalQuery(query=query, top_k=top_k, mode="hybrid"))
    return {
        "query": bundle.query,
        "chunk_count": len(bundle.chunks),
        "citations": [c.model_dump() for c in bundle.citations],
        "context": format_context_prompt(bundle),
        "token_estimate": bundle.token_estimate,
    }


def make_decision(
    question: str,
    *,
    strategy: ReasoningStrategyName = ReasoningStrategyName.ANALYTICAL,
    context: str | None = None,
) -> dict[str, Any]:
    result = DecisionPipeline().decide(
        DecisionRequest(question=question, strategy=strategy, context=context)
    )
    return {
        "decision_id": result.decision_id,
        "confidence": result.confidence,
        "recommendation": result.recommendation.model_dump() if result.recommendation else None,
        "summary": result.recommendation.summary if result.recommendation else None,
        "options_count": len(result.options),
    }


def search_memory(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    records = MemoryManager().search(MemorySearchQuery(query=query, limit=limit))
    return [
        {
            "memory_id": r.memory_id,
            "type": r.memory_type.value,
            "summary": getattr(r, "summary", None) or getattr(r, "abstraction", None) or getattr(r, "title", ""),
        }
        for r in records
    ]
