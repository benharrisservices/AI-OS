"""Embedding provider.

Local development uses Ollama (local-first). In production Ollama is not
available, so embeddings fall back to OpenAI for the lifetime of the process.
One provider is chosen once; dimensions are never mixed inside an index.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import httpx

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.io import read_json, write_json
from ai_os.knowledge.models import ChunkRecord, EmbeddingRecord, utc_now

_OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"


class DimensionMismatchError(RuntimeError):
    """Existing vector index dimensions are incompatible with the active provider."""


class EmbeddingService:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.cache_dir = settings.knowledge_index_dir / "embeddings" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Explicit config wins; otherwise auto-detect Ollama and fall back to OpenAI.
        self._use_openai = settings.embedding_provider.lower() == "openai"
        self._provider_resolved = self._use_openai
        self._index_checked = False

    # -- provider selection -------------------------------------------------

    def _ensure_provider(self) -> None:
        """Resolve the active embedding provider once per process lifetime.

        If Ollama is unreachable (typical in production), switch to OpenAI.
        After resolution, the provider is fixed — no mid-run dimension mixing.
        """
        if not self._provider_resolved:
            self._provider_resolved = True
            if not self._use_openai:
                try:
                    with httpx.Client(timeout=3.0) as client:
                        response = client.get(
                            f"{self.settings.ollama_host.rstrip('/')}/api/version"
                        )
                        response.raise_for_status()
                except Exception:
                    self._use_openai = True
        self._assert_index_compatible()

    def _assert_index_compatible(self) -> None:
        """Refuse to mix dimensions if a populated index already exists."""
        if self._index_checked:
            return
        self._index_checked = True
        try:
            from ai_os.knowledge.index.manifest import ManifestService
            from ai_os.knowledge.index.vector import VectorIndex

            count = VectorIndex(self.settings).count()
            if count <= 0:
                return
            manifest = ManifestService(self.settings).load()
            existing = manifest.embedding_dimensions
            expected = self.expected_dimensions
            if existing and existing != expected:
                raise DimensionMismatchError(
                    f"Vector index has {existing}-d embeddings but active provider "
                    f"'{self.active_provider}/{self.active_model}' produces {expected}-d. "
                    "Run a full reindex before continuing — mixing dimensions would "
                    "corrupt the index."
                )
        except DimensionMismatchError:
            raise
        except Exception:
            # Empty / uninitialized store is fine.
            return

    @property
    def active_provider(self) -> str:
        self._ensure_provider()
        return "openai" if self._use_openai else "ollama"

    @property
    def active_model(self) -> str:
        self._ensure_provider()
        return (
            self.settings.openai_embedding_model
            if self._use_openai
            else self.settings.embedding_model
        )

    @property
    def expected_dimensions(self) -> int:
        self._ensure_provider()
        return (
            self.settings.openai_embedding_dimensions
            if self._use_openai
            else self.settings.embedding_dimensions
        )

    # -- cache --------------------------------------------------------------

    def _cache_key(self, content_hash: str) -> str:
        identity = (
            f"{self.active_provider}:{self.active_model}:"
            f"{self.expected_dimensions}:{content_hash}"
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def _cache_path(self, content_hash: str) -> Path:
        return self.cache_dir / f"{self._cache_key(content_hash)}.json"

    def _load_cache(self, content_hash: str) -> list[float] | None:
        path = self._cache_path(content_hash)
        if not path.exists():
            return None
        data = read_json(path)
        if (
            data.get("embedding_provider") == self.active_provider
            and data.get("embedding_model") == self.active_model
            and data.get("embedding_dimensions") == self.expected_dimensions
        ):
            return data["vector"]
        return None

    def _save_cache(self, content_hash: str, vector: list[float]) -> None:
        write_json(
            self._cache_path(content_hash),
            {
                "content_hash": content_hash,
                "embedding_provider": self.active_provider,
                "embedding_model": self.active_model,
                "embedding_dimensions": len(vector),
                "vector": vector,
                "embedded_at": utc_now().isoformat(),
            },
        )

    # -- providers ----------------------------------------------------------

    def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
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

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OpenAI embeddings unavailable: OPENAI_API_KEY is not set")
        payload: dict = {
            "model": self.settings.openai_embedding_model,
            "input": texts,
            "dimensions": self.settings.openai_embedding_dimensions,
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.Client(timeout=120.0) as client:
            response = client.post(_OPENAI_EMBED_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        rows = data.get("data")
        if not rows:
            raise RuntimeError(f"Unexpected OpenAI embed response: {json.dumps(data)[:200]}")
        rows = sorted(rows, key=lambda r: r.get("index", 0))
        return [r["embedding"] for r in rows]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure_provider()
        if self._use_openai:
            return self._embed_openai(texts)
        return self._embed_ollama(texts)

    # -- chunk / query embedding -------------------------------------------

    def embed_chunks(self, chunks: list[ChunkRecord]) -> list[EmbeddingRecord]:
        child_chunks = [c for c in chunks if c.chunk_level.value == "child"]
        if not child_chunks:
            child_chunks = chunks
        return self.embed_chunk_list(child_chunks)

    def embed_chunk_list(self, chunks: list[ChunkRecord]) -> list[EmbeddingRecord]:
        self._ensure_provider()
        records: list[EmbeddingRecord] = []
        batch: list[ChunkRecord] = []
        batch_texts: list[str] = []

        def flush() -> None:
            nonlocal batch, batch_texts
            if not batch:
                return
            vectors = self.embed_texts(batch_texts)
            for chunk, vector in zip(batch, vectors, strict=True):
                if len(vector) != self.expected_dimensions:
                    raise DimensionMismatchError(
                        f"Embedding length {len(vector)} != expected "
                        f"{self.expected_dimensions} for {self.active_provider}"
                    )
                self._save_cache(chunk.content_hash, vector)
                records.append(
                    EmbeddingRecord(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        content_hash=chunk.content_hash,
                        embedding_model=self.active_model,
                        embedding_provider=self.active_provider,
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
                        embedding_model=self.active_model,
                        embedding_provider=self.active_provider,
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
        self._ensure_provider()
        cached = self._load_cache(f"query:{query}")
        if cached is not None:
            return cached
        vector = self.embed_texts([query])[0]
        self._save_cache(f"query:{query}", vector)
        return vector
