"""BM25 keyword index."""

from __future__ import annotations

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.models import ChunkRecord, SearchHit

_TOKEN_RE = re.compile(r"\w+")


class KeywordIndex:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.path = settings.knowledge_index_dir / "keyword" / "bm25.json"
        self._chunk_ids: list[str] = []
        self._corpus_meta: list[dict[str, str]] = []
        self._bm25: BM25Okapi | None = None
        self._load()

    def _tokenize(self, text: str) -> list[str]:
        return [t.lower() for t in _TOKEN_RE.findall(text)]

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._chunk_ids = data["chunk_ids"]
        self._corpus_meta = data["metadata"]
        corpus = data["corpus"]
        self._bm25 = BM25Okapi(corpus)

    def _save(self, corpus_tokens: list[list[str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunk_ids": self._chunk_ids,
            "metadata": self._corpus_meta,
            "corpus": corpus_tokens,
        }
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def rebuild(self, chunks: list[ChunkRecord]) -> None:
        child_chunks = [c for c in chunks if c.chunk_level.value == "child"]
        self._chunk_ids = []
        self._corpus_meta = []
        corpus_tokens: list[list[str]] = []

        for chunk in child_chunks:
            text = f"{chunk.title} {chunk.heading_path} {chunk.embed_text}"
            self._chunk_ids.append(chunk.chunk_id)
            self._corpus_meta.append(
                {
                    "doc_id": chunk.doc_id,
                    "source_id": chunk.source_id,
                    "title": chunk.title,
                    "heading_path": chunk.heading_path,
                    "excerpt": chunk.body_text[:240],
                    "source_uri": chunk.source_id,
                }
            )
            corpus_tokens.append(self._tokenize(text))

        self._bm25 = BM25Okapi(corpus_tokens) if corpus_tokens else None
        if corpus_tokens:
            self._save(corpus_tokens)

    def search(self, query: str, top_k: int) -> list[SearchHit]:
        if self._bm25 is None or not self._chunk_ids:
            return []
        tokens = self._tokenize(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]

        hits: list[SearchHit] = []
        for index, score in ranked:
            if score <= 0:
                continue
            meta = self._corpus_meta[index]
            hits.append(
                SearchHit(
                    chunk_id=self._chunk_ids[index],
                    doc_id=meta["doc_id"],
                    source_id=meta["source_id"],
                    score=float(score),
                    scores={"keyword": float(score)},
                    title=meta["title"],
                    heading_path=meta["heading_path"],
                    excerpt=meta["excerpt"],
                    source_uri=meta["source_uri"],
                )
            )
        return hits
