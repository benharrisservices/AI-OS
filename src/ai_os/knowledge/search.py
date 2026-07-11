"""Hybrid search with reciprocal rank fusion."""

from __future__ import annotations

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.embedding import EmbeddingService
from ai_os.knowledge.index.keyword import KeywordIndex
from ai_os.knowledge.index.vector import VectorIndex
from ai_os.knowledge.models import SearchHit, SearchQuery


def reciprocal_rank_fusion(
    result_lists: list[list[SearchHit]],
    k: int = 60,
) -> list[SearchHit]:
    scores: dict[str, float] = {}
    payloads: dict[str, SearchHit] = {}

    for results in result_lists:
        for rank, hit in enumerate(results, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            existing = payloads.get(hit.chunk_id)
            if existing is None:
                payloads[hit.chunk_id] = hit
            else:
                merged_scores = {**existing.scores, **hit.scores}
                payloads[hit.chunk_id] = existing.model_copy(
                    update={"scores": merged_scores}
                )

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    fused: list[SearchHit] = []
    for chunk_id, fusion_score in ranked:
        hit = payloads[chunk_id]
        fused.append(
            hit.model_copy(
                update={
                    "score": fusion_score,
                    "scores": {**hit.scores, "fusion": fusion_score},
                }
            )
        )
    return fused


class HybridSearch:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.embedder = EmbeddingService(settings)
        self.vector = VectorIndex(settings)
        self.keyword = KeywordIndex(settings)

    def search(self, query: SearchQuery) -> list[SearchHit]:
        mode = query.mode.lower()
        top_k = query.top_k or self.settings.search_top_k

        vector_hits: list[SearchHit] = []
        keyword_hits: list[SearchHit] = []

        if mode in {"hybrid", "vector"}:
            query_vector = self.embedder.embed_query(query.query)
            vector_hits = self.vector.search(query_vector, self.settings.vector_top_k)

        if mode in {"hybrid", "keyword"}:
            keyword_hits = self.keyword.search(query.query, self.settings.keyword_top_k)

        if mode == "vector":
            return vector_hits[:top_k]
        if mode == "keyword":
            return keyword_hits[:top_k]

        fused = reciprocal_rank_fusion(
            [vector_hits, keyword_hits],
            k=self.settings.hybrid_rrf_k,
        )
        return fused[:top_k]
