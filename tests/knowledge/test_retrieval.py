from pathlib import Path
from unittest.mock import patch

import pytest

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.models import RetrievalQuery
from ai_os.knowledge.pipeline import KnowledgePipeline
from ai_os.knowledge.retrieval import KnowledgeRetrieval, format_context_prompt


@pytest.fixture
def pipeline(tmp_path: Path) -> KnowledgePipeline:
    settings = KnowledgeSettings(
        KNOWLEDGE_RAW_DIR=tmp_path / "raw",
        KNOWLEDGE_PROCESSED_DIR=tmp_path / "processed",
        KNOWLEDGE_INDEX_DIR=tmp_path / "index",
        VECTOR_STORE_PATH=tmp_path / "index" / "vectors",
        EMBEDDING_BATCH_SIZE=8,
    )
    return KnowledgePipeline(settings)


def _fake_embeddings(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        vec = [float(len(text) % 7), 0.1, 0.2] + [0.0] * 765
        vectors.append(vec[:768])
    return vectors


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_retrieve_returns_context_bundle(mock_embed, pipeline: KnowledgePipeline) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))

    engine = KnowledgeRetrieval(pipeline.settings)
    bundle = engine.retrieve(RetrievalQuery(query="Barbados solar", top_k=5))

    assert bundle.chunks
    assert bundle.citations
    assert len(bundle.chunks) == len(bundle.citations)
    assert bundle.token_estimate > 0
    assert bundle.retrieval_metadata.search_mode == "hybrid"


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_citations_are_numbered_in_order(mock_embed, pipeline: KnowledgePipeline) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))

    engine = KnowledgeRetrieval(pipeline.settings)
    bundle = engine.retrieve(RetrievalQuery(query="solar incentives", top_k=5))

    keys = [c.cite_key for c in bundle.citations]
    assert keys == [f"[{i}]" for i in range(1, len(keys) + 1)]
    assert all(c.title == "Barbados Solar Project" for c in bundle.citations)


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_max_chunks_per_doc_limits_results(mock_embed, pipeline: KnowledgePipeline) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))

    engine = KnowledgeRetrieval(pipeline.settings)
    bundle = engine.retrieve(
        RetrievalQuery(query="Barbados solar", top_k=10, max_chunks_per_doc=1)
    )

    doc_ids = [chunk.doc_id for chunk in bundle.chunks]
    assert len(doc_ids) == len(set(doc_ids))


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_token_budget_trims(mock_embed, pipeline: KnowledgePipeline) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))

    engine = KnowledgeRetrieval(pipeline.settings)
    bundle = engine.retrieve(
        RetrievalQuery(query="Barbados solar", top_k=10, max_tokens=5, max_chunks_per_doc=10)
    )

    assert len(bundle.chunks) == 1  # budget allows only the first chunk


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_format_context_prompt_includes_citations(mock_embed, pipeline: KnowledgePipeline) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))

    engine = KnowledgeRetrieval(pipeline.settings)
    bundle = engine.retrieve(RetrievalQuery(query="Kickstarter", top_k=5))
    prompt = format_context_prompt(bundle)

    assert "[1]" in prompt
    assert "Sources:" in prompt
    assert "Barbados Solar Project" in prompt


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_expand_parent_uses_parent_text(mock_embed, pipeline: KnowledgePipeline) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))

    engine = KnowledgeRetrieval(pipeline.settings)
    child = engine.retrieve(
        RetrievalQuery(query="Kickstarter", top_k=3, retrieval_mode="search")
    )
    parent = engine.retrieve(
        RetrievalQuery(query="Kickstarter", top_k=3, retrieval_mode="expand_parent")
    )

    assert child.chunks
    assert parent.chunks
    # Parent expansion should return text at least as long as the child text.
    assert len(parent.chunks[0].text) >= len(child.chunks[0].text)
