"""ChromaDB vector index."""

from __future__ import annotations

from typing import Any

import chromadb

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.models import ChunkRecord, EmbeddingRecord, SearchHit


class VectorIndex:
    COLLECTION = "ai_os_chunks"

    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.client = chromadb.PersistentClient(path=str(settings.vector_store_path))
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def delete_doc(self, doc_id: str) -> None:
        try:
            self.collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass

    def upsert(
        self,
        chunks: list[ChunkRecord],
        embeddings: list[EmbeddingRecord],
    ) -> None:
        chunk_by_id = {c.chunk_id: c for c in chunks}
        ids: list[str] = []
        vectors: list[list[float]] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for embedding in embeddings:
            chunk = chunk_by_id.get(embedding.chunk_id)
            if chunk is None:
                continue
            ids.append(chunk.chunk_id)
            vectors.append(embedding.vector)
            documents.append(chunk.body_text)
            metadatas.append(
                {
                    "doc_id": chunk.doc_id,
                    "source_id": chunk.source_id,
                    "title": chunk.title,
                    "heading_path": chunk.heading_path,
                    "language": chunk.language,
                    "tags": ",".join(chunk.tags),
                }
            )

        if ids:
            self.collection.upsert(
                ids=ids,
                embeddings=vectors,
                documents=documents,
                metadatas=metadatas,
            )

    def search(self, query_vector: list[float], top_k: int) -> list[SearchHit]:
        if self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        hits: list[SearchHit] = []
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]

        for chunk_id, distance, document, metadata in zip(
            ids, distances, documents, metadatas, strict=True
        ):
            score = 1.0 - float(distance)
            excerpt = (document or "")[:240]
            hits.append(
                SearchHit(
                    chunk_id=chunk_id,
                    doc_id=metadata.get("doc_id", ""),
                    source_id=metadata.get("source_id", ""),
                    score=score,
                    scores={"vector": score},
                    title=metadata.get("title", ""),
                    heading_path=metadata.get("heading_path", ""),
                    excerpt=excerpt,
                    source_uri=metadata.get("source_id", ""),
                )
            )
        return hits
