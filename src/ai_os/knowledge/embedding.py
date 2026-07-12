"""Ollama embedding provider."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.io import read_json, write_json
from ai_os.knowledge.models import ChunkRecord, EmbeddingRecord, utc_now


class EmbeddingService:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.cache_dir = settings.knowledge_index_dir / "embeddings" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, content_hash: str) -> Path:
        if len(content_hash) > 120:
            content_hash = hashlib.sha256(content_hash.encode("utf-8")).hexdigest()
        safe = content_hash.replace(":", "_")
        return self.cache_dir / f"{safe}.json"

    def _load_cache(self, content_hash: str) -> list[float] | None:
        path = self._cache_path(content_hash)
        if not path.exists():
            return None
        data = read_json(path)
        if (
            data.get("embedding_model") == self.settings.embedding_model
            and data.get("embedding_dimensions") == self.settings.embedding_dimensions
        ):
            return data["vector"]
        return None

    def _save_cache(self, content_hash: str, vector: list[float]) -> None:
        write_json(
            self._cache_path(content_hash),
            {
                "content_hash": content_hash,
                "embedding_model": self.settings.embedding_model,
                "embedding_dimensions": self.settings.embedding_dimensions,
                "vector": vector,
                "embedded_at": utc_now().isoformat(),
            },
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        url = f"{self.settings.ollama_host.rstrip('/')}/api/embed"
        payload = {"model": self.settings.embedding_model, "input": texts}
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        embeddings = data.get("embeddings")
        if embeddings is None and "embedding" in data:
            embeddings = [data["embedding"]]
        if not embeddings:
            raise RuntimeError(f"Unexpected Ollama embed response: {json.dumps(data)[:200]}")
        return embeddings

    def embed_chunks(self, chunks: list[ChunkRecord]) -> list[EmbeddingRecord]:
        child_chunks = [c for c in chunks if c.chunk_level.value == "child"]
        if not child_chunks:
            child_chunks = chunks
        return self.embed_chunk_list(child_chunks)

    def embed_chunk_list(self, chunks: list[ChunkRecord]) -> list[EmbeddingRecord]:
        records: list[EmbeddingRecord] = []
        batch: list[ChunkRecord] = []
        batch_texts: list[str] = []

        def flush() -> None:
            nonlocal batch, batch_texts
            if not batch:
                return
            vectors = self.embed_texts(batch_texts)
            for chunk, vector in zip(batch, vectors, strict=True):
                self._save_cache(chunk.content_hash, vector)
                records.append(
                    EmbeddingRecord(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        content_hash=chunk.content_hash,
                        embedding_model=self.settings.embedding_model,
                        embedding_provider=self.settings.embedding_provider,
                        embedding_dimensions=len(vector),
                        vector=vector,
                        cache_hit=False,
                    )
                )
            batch = []
            batch_texts = []

        for chunk in chunks:
            cached = self._load_cache(chunk.content_hash)
            if cached is not None:
                records.append(
                    EmbeddingRecord(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        content_hash=chunk.content_hash,
                        embedding_model=self.settings.embedding_model,
                        embedding_provider=self.settings.embedding_provider,
                        embedding_dimensions=len(cached),
                        vector=cached,
                        cache_hit=True,
                    )
                )
                continue
            batch.append(chunk)
            batch_texts.append(chunk.embed_text)
            if len(batch) >= self.settings.embedding_batch_size:
                flush()
        flush()
        return records

    def purge_cache_hashes(self, content_hashes: list[str]) -> int:
        removed = 0
        for content_hash in content_hashes:
            path = self._cache_path(content_hash)
            if path.exists():
                path.unlink()
                removed += 1
        return removed

    def embed_query(self, query: str) -> list[float]:
        cached = self._load_cache(f"query:{query}")
        if cached is not None:
            return cached
        vector = self.embed_texts([query])[0]
        self._save_cache(f"query:{query}", vector)
        return vector
