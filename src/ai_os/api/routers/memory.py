"""Memory API — wraps MemoryManager and MemoryIntelligence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ai_os.api.auth import require_api_key
from ai_os.api.serialize import to_json
from ai_os.memory.intelligence import MemoryIntelligence
from ai_os.memory.manager import MemoryManager
from ai_os.memory.models import MemorySearchQuery, MemoryType

router = APIRouter(prefix="/memory", tags=["memory"])


class MemorySearchBody(BaseModel):
    query: str = ""
    limit: int = 20
    memory_type: str | None = None


@router.get("")
def list_memories(
    memory_type: str | None = Query(None),
    limit: int = Query(50, le=200),
) -> list:
    mgr = MemoryManager()
    if memory_type:
        try:
            mt = MemoryType(memory_type)
            records = mgr.list_by_type(mt, status=None)[:limit]
        except ValueError:
            records = mgr.list_all(status=None)[:limit]
    else:
        records = mgr.list_all(status=None)[:limit]
    return [to_json(r) for r in records]


@router.post("/search")
def search_memory(body: MemorySearchBody) -> list:
    types = [MemoryType(body.memory_type)] if body.memory_type else []
    query = MemorySearchQuery(query=body.query, limit=body.limit, memory_types=types)
    return [to_json(r) for r in MemoryManager().search(query)]


@router.get("/insights/summary")
def memory_insights() -> dict:
    intel = MemoryIntelligence()
    return {
        "duplicates": intel.detect_duplicates(),
        "clusters": intel.cluster_semantic(),
        "contradictions": intel.detect_contradictions(),
        "promotions": [to_json(p) for p in intel.promotion_recommendations()],
        "graph": intel.build_relationship_graph(),
    }


@router.get("/timeline/events")
def memory_timeline(query: str = "", limit: int = 20) -> list:
    return MemoryIntelligence().build_timeline(query=query, limit=limit)


@router.get("/{memory_id}")
def get_memory(memory_id: str) -> dict:
    record = MemoryManager().get(memory_id)
    if not record:
        raise HTTPException(404, "Memory not found")
    return to_json(record)


@router.post("/{memory_id}/promote", dependencies=[Depends(require_api_key)])
def promote_memory(memory_id: str) -> dict:
    from ai_os.memory.models import PromotionRequest

    result = MemoryManager().promote(PromotionRequest(memory_id=memory_id))
    return to_json(result)


@router.post("/{memory_id}/archive", dependencies=[Depends(require_api_key)])
def archive_memory(memory_id: str) -> dict:
    record = MemoryManager().archive(memory_id)
    if not record:
        raise HTTPException(404, "Memory not found")
    return to_json(record)
