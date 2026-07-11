from pathlib import Path
from unittest.mock import patch

import pytest

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.pipeline import KnowledgePipeline


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
def test_pipeline_ingest_and_search(mock_embed, pipeline: KnowledgePipeline) -> None:
    fixture = Path("tests/fixtures/barbados-solar.md")
    pipeline.ingest_file(fixture)

    from ai_os.knowledge.models import SearchQuery
    from ai_os.knowledge.search import HybridSearch

    hits = HybridSearch(pipeline.settings).search(SearchQuery(query="Barbados solar", top_k=5))
    assert hits
    assert any("Barbados" in hit.excerpt or "solar" in hit.excerpt.lower() for hit in hits)


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_pipeline_search_ultra_mobile(mock_embed, pipeline: KnowledgePipeline) -> None:
    fixture = Path("tests/fixtures/barbados-solar.md")
    pipeline.ingest_file(fixture)

    from ai_os.knowledge.models import SearchQuery
    from ai_os.knowledge.search import HybridSearch

    hits = HybridSearch(pipeline.settings).search(SearchQuery(query="Ultra Mobile", top_k=5))
    assert hits
    assert any("Ultra Mobile" in hit.excerpt for hit in hits)


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_pipeline_search_kickstarter(mock_embed, pipeline: KnowledgePipeline) -> None:
    fixture = Path("tests/fixtures/barbados-solar.md")
    pipeline.ingest_file(fixture)

    from ai_os.knowledge.models import SearchQuery
    from ai_os.knowledge.search import HybridSearch

    hits = HybridSearch(pipeline.settings).search(SearchQuery(query="Kickstarter", top_k=5))
    assert hits
    assert any("Kickstarter" in hit.excerpt for hit in hits)
