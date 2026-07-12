"""Knowledge API — wraps Knowledge Engine services."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ai_os.api.serialize import to_json
from ai_os.knowledge.config import get_settings
from ai_os.knowledge.health import HealthService
from ai_os.knowledge.maintenance import MaintenanceService
from ai_os.knowledge.models import RetrievalQuery, SearchQuery
from ai_os.knowledge.registry import SourceRegistry
from ai_os.knowledge.retrieval import KnowledgeRetrieval
from ai_os.knowledge.search import HybridSearch
from ai_os.knowledge.store import ChunkStore

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class SearchBody(BaseModel):
    query: str
    mode: str = "hybrid"
    top_k: int = 10


class RetrieveBody(BaseModel):
    query: str
    mode: str = "hybrid"
    top_k: int = 8
    max_tokens: int = 4000
    max_chunks_per_doc: int = 2


@router.get("/status")
def knowledge_status() -> dict:
    report = HealthService(get_settings()).report(run_integrity=False)
    return to_json(report)


@router.get("/sources")
def list_sources() -> list:
    registry = SourceRegistry(get_settings())
    return [to_json(r) for r in registry.list_ready()]


@router.get("/documents")
def list_documents() -> list:
    settings = get_settings()
    docs_root = settings.knowledge_processed_dir / "documents"
    if not docs_root.exists():
        return []
    store = ChunkStore(settings)
    results = []
    for doc_dir in sorted(docs_root.iterdir()):
        if not doc_dir.is_dir():
            continue
        doc_id = doc_dir.name
        meta_path = doc_dir / "document.meta.json"
        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        results.append({
            "doc_id": doc_id,
            "title": store.get_title(doc_id) or meta.get("title", doc_id),
            "source_uri": store.get_source_uri(doc_id),
            "meta": meta,
        })
    return results


@router.get("/documents/{doc_id}")
def get_document(doc_id: str) -> dict:
    store = ChunkStore(get_settings())
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    chunks_dir = get_settings().knowledge_processed_dir / "documents" / doc_id / "chunks"
    chunks = []
    if chunks_dir.exists():
        for chunk_file in sorted(chunks_dir.glob("*.json")):
            chunk_id = chunk_file.stem
            chunk = store.get_chunk(doc_id, chunk_id)
            if chunk:
                chunks.append(to_json(chunk))
    return {"document": to_json(doc), "chunks": chunks}


@router.post("/search")
def search_knowledge(body: SearchBody) -> list:
    hits = HybridSearch(get_settings()).search(
        SearchQuery(query=body.query, mode=body.mode, top_k=body.top_k)
    )
    return [to_json(h) for h in hits]


@router.post("/retrieve")
def retrieve_knowledge(body: RetrieveBody) -> dict:
    bundle = KnowledgeRetrieval(get_settings()).retrieve(
        RetrievalQuery(
            query=body.query,
            mode=body.mode,
            top_k=body.top_k,
            max_tokens=body.max_tokens,
            max_chunks_per_doc=body.max_chunks_per_doc,
        )
    )
    return to_json(bundle)


@router.post("/reindex")
def reindex_knowledge() -> dict:
    MaintenanceService(get_settings()).ensure_search_indexes()
    return {"status": "ok", "message": "Reindex complete"}


@router.get("/doctor")
def knowledge_doctor() -> dict:
    return to_json(MaintenanceService(get_settings()).doctor())
