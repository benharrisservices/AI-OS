"""Retrieval pipeline: assemble a ContextBundle for RAG consumers."""

from __future__ import annotations

import time

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.models import (
    Citation,
    ContextBundle,
    RetrievalMetadata,
    RetrievalQuery,
    RetrievedChunk,
    SearchHit,
    SearchQuery,
)
from ai_os.knowledge.search import HybridSearch
from ai_os.knowledge.store import ChunkStore
from ai_os.knowledge.tokens import count_tokens


class KnowledgeRetrieval:
    """Turns a query into ranked, deduplicated, citation-backed context.

    Retrieval sits on top of hybrid search and prepares context for the
    decision engine. It never calls an LLM; it only assembles context.
    """

    def __init__(self, settings: KnowledgeSettings | None = None) -> None:
        self.settings = settings or KnowledgeSettings()
        self.search = HybridSearch(self.settings)
        self.store = ChunkStore(self.settings)

    def retrieve(self, query: RetrievalQuery) -> ContextBundle:
        start = time.perf_counter()

        hits = self.search.search(
            SearchQuery(
                query=query.query,
                mode=query.mode,
                top_k=max(query.top_k * 3, query.top_k),
                filters=query.filters,
            )
        )

        deduped = self._dedupe_by_doc(hits, query.max_chunks_per_doc)[: query.top_k]
        expand = query.retrieval_mode == "expand_parent" or (
            query.retrieval_mode == "context" and query.expand_parents
        )

        retrieved = self._materialize(deduped, expand=expand)
        trimmed = self._trim_to_budget(retrieved, query.max_tokens)
        citations = self._build_citations(trimmed)
        token_estimate = sum(count_tokens(chunk.text) for chunk in trimmed)
        latency_ms = int((time.perf_counter() - start) * 1000)

        return ContextBundle(
            query=query.query,
            chunks=trimmed,
            citations=citations,
            token_estimate=token_estimate,
            retrieval_metadata=RetrievalMetadata(
                search_mode=query.mode,
                rerank_enabled=False,
                latency_ms=latency_ms,
            ),
        )

    def _dedupe_by_doc(self, hits: list[SearchHit], max_per_doc: int) -> list[SearchHit]:
        seen: dict[str, int] = {}
        kept: list[SearchHit] = []
        for hit in hits:
            count = seen.get(hit.doc_id, 0)
            if count >= max_per_doc:
                continue
            seen[hit.doc_id] = count + 1
            kept.append(hit)
        return kept

    def _materialize(self, hits: list[SearchHit], *, expand: bool) -> list[RetrievedChunk]:
        results: list[RetrievedChunk] = []
        for hit in hits:
            chunk = self.store.get_chunk(hit.doc_id, hit.chunk_id)
            text = chunk.body_text if chunk else hit.excerpt

            if expand and chunk and chunk.parent_chunk_id:
                parent = self.store.get_chunk(hit.doc_id, chunk.parent_chunk_id)
                if parent:
                    text = parent.body_text

            source_uri = self.store.get_source_uri(hit.doc_id) or hit.source_uri
            results.append(
                RetrievedChunk(
                    chunk_id=hit.chunk_id,
                    doc_id=hit.doc_id,
                    text=text,
                    score=hit.score,
                    heading_path=hit.heading_path,
                    source_uri=source_uri,
                )
            )
        return results

    def _trim_to_budget(self, chunks: list[RetrievedChunk], max_tokens: int) -> list[RetrievedChunk]:
        trimmed: list[RetrievedChunk] = []
        running = 0
        for chunk in chunks:
            tokens = count_tokens(chunk.text)
            if trimmed and running + tokens > max_tokens:
                break
            trimmed.append(chunk)
            running += tokens
        return trimmed

    def _build_citations(self, chunks: list[RetrievedChunk]) -> list[Citation]:
        citations: list[Citation] = []
        for index, chunk in enumerate(chunks, start=1):
            title = self.store.get_title(chunk.doc_id) or chunk.doc_id
            citations.append(
                Citation(
                    cite_key=f"[{index}]",
                    chunk_id=chunk.chunk_id,
                    title=title,
                    source_uri=chunk.source_uri,
                    excerpt=chunk.text[:240],
                )
            )
        return citations


def format_context_prompt(bundle: ContextBundle) -> str:
    """Render a prompt-ready context string with citation markers.

    Downstream prompt templates fill ``{{knowledge_context}}`` with this.
    """
    blocks: list[str] = []
    for citation, chunk in zip(bundle.citations, bundle.chunks, strict=True):
        blocks.append(f"{citation.cite_key} {citation.title}\n{chunk.text}")

    sources = "\n".join(
        f"{c.cite_key} {c.title} — {c.source_uri}" for c in bundle.citations
    )
    context = "\n\n".join(blocks)
    return f"{context}\n\nSources:\n{sources}" if sources else context
