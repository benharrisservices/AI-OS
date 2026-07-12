"""Dashboard API — aggregates existing CLI/service data."""

from __future__ import annotations

from fastapi import APIRouter

from ai_os.api.serialize import to_json
from ai_os.automation.config import get_automation_settings
from ai_os.automation.service import AutomationService
from ai_os.capabilities.registry import discover_skills, list_skills
from ai_os.decision.config import get_decision_settings
from ai_os.decision.store import DecisionStore
from ai_os.integrations.registry import discover_providers, health_check_all, list_providers
from ai_os.knowledge.config import get_settings
from ai_os.knowledge.health import HealthService
from ai_os.knowledge.search import HybridSearch
from ai_os.knowledge.models import SearchQuery
from ai_os.memory.manager import MemoryManager
from ai_os.routing.config import RoutingSettings
from ai_os.routing.models import ModelRequest
from ai_os.routing.router import ModelRouter
from ai_os.agent.config import get_agent_settings
from ai_os.agent.workflows import WorkflowLoader
from ai_os.agent.store import TaskStore

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard() -> dict:
    settings = get_settings()
    health = HealthService(settings).report(run_integrity=False)
    discover_skills()
    skills = list_skills()
    automations = AutomationService(get_automation_settings()).list_automations()
    memories = MemoryManager().list_all(status=None)
    discover_providers()
    providers = list_providers()
    provider_health = health_check_all()
    healthy_count = sum(1 for h in provider_health if h.status.value == "healthy")
    decisions = DecisionStore(get_decision_settings()).list_all()[:5]
    workflows = WorkflowLoader(get_agent_settings()).list_workflows()
    tasks = TaskStore(get_agent_settings()).list_tasks()[:10]
    activity = AutomationService(get_automation_settings()).history(limit=10)
    route = ModelRouter().route(ModelRequest(task="daily briefing"))
    recent_knowledge = HybridSearch(settings).search(SearchQuery(query="architecture", top_k=5))

    return {
        "status": "healthy" if health.healthy else "needs_attention",
        "counts": {
            "skills": len(skills),
            "automations": len(automations),
            "memories": len(memories),
            "providers": len(providers),
            "providers_healthy": healthy_count,
            "workflows": len(workflows),
            "sources": health.source_count,
            "documents": health.document_count,
            "chunks": health.chunk_count,
        },
        "health": to_json(health),
        "provider_health": [to_json(h) for h in provider_health],
        "model_route": to_json(route),
        "routing_settings": to_json(RoutingSettings()),
        "recent_decisions": [to_json(d) for d in decisions],
        "recent_memories": [to_json(m) for m in memories[:5]],
        "recent_knowledge": [to_json(h) for h in recent_knowledge],
        "recent_activity": [to_json(a) for a in activity],
        "recent_tasks": [to_json(t) for t in tasks],
        "workflows": [to_json(w) for w in workflows],
        "automations": [to_json(a) for a in automations],
    }
