"""Embedding cache path tests."""

from ai_os.knowledge.embedding import EmbeddingService
from ai_os.knowledge.config import KnowledgeSettings


class TestEmbeddingCache:
    def test_long_query_cache_path(self, tmp_path) -> None:
        settings = KnowledgeSettings(knowledge_index_dir=tmp_path / "index")
        service = EmbeddingService(settings)
        long_query = "x" * 5000
        path = service._cache_path(f"query:{long_query}")
        assert len(path.name) < 200
