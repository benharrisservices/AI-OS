"""Full-system validation for production readiness."""

from __future__ import annotations

import importlib
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from ai_os.agent.workflows import WorkflowLoader
from ai_os.agent.config import AgentSettings
from ai_os.automation.config import AutomationSettings
from ai_os.automation.service import AutomationService
from ai_os.capabilities.registry import discover_skills, list_skills
from ai_os.decision.strategies import list_strategies
from ai_os.integrations.registry import discover_providers, health_check_all
from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.health import HealthService
from ai_os.memory.config import MemorySettings
from ai_os.memory.manager import MemoryManager
from ai_os.routing.router import ModelRouter
from ai_os.routing.models import ModelRequest


@dataclass
class CheckResult:
    name: str
    status: str  # ok, warn, fail
    detail: str = ""
    duration_ms: int = 0


@dataclass
class SystemReport:
    results: list[CheckResult] = field(default_factory=list)
    healthy: bool = True

    def add(self, result: CheckResult) -> None:
        self.results.append(result)
        if result.status == "fail":
            self.healthy = False


def run_benchmarks() -> list[CheckResult]:
    """Run lightweight performance benchmarks for startup diagnostics."""
    results: list[CheckResult] = []

    def bench(name: str, fn) -> None:
        start = time.perf_counter()
        try:
            fn()
            ms = int((time.perf_counter() - start) * 1000)
            results.append(CheckResult(name=name, status="ok", detail=f"{ms}ms", duration_ms=ms))
        except Exception as exc:
            ms = int((time.perf_counter() - start) * 1000)
            results.append(CheckResult(name=name, status="fail", detail=str(exc), duration_ms=ms))

    from ai_os.knowledge.config import KnowledgeSettings
    from ai_os.knowledge.search import HybridSearch
    from ai_os.knowledge.models import SearchQuery

    settings = KnowledgeSettings()
    bench("workflow_load", lambda: WorkflowLoader(AgentSettings()).list_workflows())
    bench("skill_discovery", lambda: discover_skills())
    bench("provider_health", lambda: health_check_all())
    bench("memory_list", lambda: MemoryManager(MemorySettings()).list_all(status=None))
    bench("knowledge_search", lambda: HybridSearch(settings).search(SearchQuery(query="test", top_k=3)))
    bench("model_route", lambda: ModelRouter().route(ModelRequest(task="benchmark")))
    return results


def run_full_check(*, include_benchmarks: bool = False) -> SystemReport:
    report = SystemReport()

    def timed(name: str, fn) -> None:
        start = time.perf_counter()
        try:
            detail = fn()
            ms = int((time.perf_counter() - start) * 1000)
            report.add(CheckResult(name=name, status="ok", detail=detail, duration_ms=ms))
        except Exception as exc:
            ms = int((time.perf_counter() - start) * 1000)
            report.add(CheckResult(name=name, status="fail", detail=str(exc), duration_ms=ms))

    timed("python_version", lambda: f"{sys.version_info.major}.{sys.version_info.minor}")
    timed("dependencies", _check_dependencies)
    timed("knowledge_engine", _check_knowledge)
    timed("decision_engine", lambda: f"{len(list_strategies())} strategies")
    timed("memory_system", _check_memory)
    timed("agent_runtime", _check_agent)
    timed("automation_layer", _check_automation)
    timed("capabilities", _check_capabilities)
    timed("integrations", _check_integrations)
    timed("model_router", _check_router)
    timed("configuration", _check_config_paths)

    from ai_os.knowledge.maintenance import MaintenanceService

    def _check_backup() -> str:
        ok, msg = MaintenanceService(KnowledgeSettings()).verify_backup()
        if not ok and "No backups found" in msg:
            return "no backups yet (run: ai-os backup)"
        if not ok:
            raise RuntimeError(msg)
        return msg

    timed("backup_verification", _check_backup)

    if include_benchmarks:
        for bench in run_benchmarks():
            report.add(bench)

    return report


def _check_dependencies() -> str:
    required = ["pydantic", "typer", "httpx", "yaml", "chromadb", "rich"]
    missing = []
    for pkg in required:
        try:
            importlib.import_module(pkg if pkg != "yaml" else "yaml")
        except ImportError:
            missing.append(pkg)
    if missing:
        raise RuntimeError(f"Missing packages: {', '.join(missing)}")
    return f"{len(required)} core packages"


def _check_knowledge() -> str:
    settings = KnowledgeSettings()
    settings.ensure_dirs()
    health = HealthService(settings).report(run_integrity=False)
    return f"docs={health.document_count} chunks={health.chunk_count} ollama={health.ollama_available}"


def _check_memory() -> str:
    settings = MemorySettings()
    settings.ensure_dirs()
    count = len(MemoryManager(settings).list_all(status=None))
    return f"{count} memories"


def _check_agent() -> str:
    settings = AgentSettings()
    settings.ensure_dirs()
    workflows = WorkflowLoader(settings).list_workflows()
    return f"{len(workflows)} workflows"


def _check_automation() -> str:
    settings = AutomationSettings()
    settings.ensure_dirs()
    count = len(AutomationService(settings).list_automations())
    return f"{count} automations"


def _check_capabilities() -> str:
    discover_skills()
    return f"{len(list_skills())} skills"


def _check_integrations() -> str:
    discover_providers()
    health = health_check_all()
    healthy = sum(1 for h in health if h.status.value == "healthy")
    return f"{healthy}/{len(health)} healthy"


def _check_router() -> str:
    route = ModelRouter().route(ModelRequest(task="health check"))
    return f"{route.provider_id}/{route.model_id}"


def _check_config_paths() -> str:
    paths = [
        Path("./config/workflows"),
        Path("./config/automations"),
        Path("./config/agents"),
        Path("./.env.example"),
    ]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise RuntimeError(f"Missing: {', '.join(missing)}")
    return f"{len(paths)} paths verified"
