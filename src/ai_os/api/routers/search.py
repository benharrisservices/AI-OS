"""Global search API — composes existing search interfaces."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ai_os.api.serialize import to_json
from ai_os.agent.config import get_agent_settings
from ai_os.agent.workflows import WorkflowLoader
from ai_os.automation.config import get_automation_settings
from ai_os.automation.service import AutomationService
from ai_os.decision.config import get_decision_settings
from ai_os.decision.store import DecisionStore
from ai_os.knowledge.config import get_settings
from ai_os.knowledge.models import SearchQuery
from ai_os.knowledge.search import HybridSearch
from ai_os.memory.manager import MemoryManager
from ai_os.memory.models import MemorySearchQuery

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(q: str = Query(..., min_length=1), limit: int = Query(10, le=50)) -> dict:
    query_lower = q.lower()
    knowledge = HybridSearch(get_settings()).search(SearchQuery(query=q, top_k=limit))
    memories = MemoryManager().search(MemorySearchQuery(query=q, limit=limit))
    decisions = [
        d for d in DecisionStore(get_decision_settings()).list_all()
        if query_lower in d.request.question.lower()
    ][:limit]
    workflows = [
        w for w in WorkflowLoader(get_agent_settings()).list_workflows()
        if query_lower in w.name.lower() or query_lower in (w.description or "").lower()
    ][:limit]
    automations = [
        a for a in AutomationService(get_automation_settings()).list_automations()
        if query_lower in a.name.lower() or query_lower in (a.description or "").lower()
    ][:limit]

    return {
        "query": q,
        "knowledge": [to_json(h) for h in knowledge],
        "memories": [to_json(m) for m in memories],
        "decisions": [to_json(d) for d in decisions],
        "workflows": [to_json(w) for w in workflows],
        "automations": [to_json(a) for a in automations],
    }
