"""Settings and system diagnostics API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ai_os.api.auth import require_api_key
from ai_os.api.serialize import to_json
from ai_os.agent.config import AgentSettings
from ai_os.automation.config import AutomationSettings
from ai_os.decision.config import DecisionSettings
from ai_os.integrations.config import IntegrationSettings
from ai_os.knowledge.config import KnowledgeSettings
from ai_os.memory.config import MemorySettings
from ai_os.routing.config import RoutingSettings
from ai_os.setup import run_setup
from ai_os.system_check import run_full_check

router = APIRouter(prefix="/settings", tags=["settings"])

SECRET_KEYS = {"api_key", "token", "secret", "password", "credential"}


def _redact_settings(model) -> dict:
    data = model.model_dump()
    for key in list(data.keys()):
        lower = key.lower()
        if any(s in lower for s in SECRET_KEYS):
            data[key] = "***" if data[key] else ""
    return data


@router.get("")
def get_settings() -> dict:
    return {
        "knowledge": _redact_settings(KnowledgeSettings()),
        "memory": _redact_settings(MemorySettings()),
        "decision": _redact_settings(DecisionSettings()),
        "agent": _redact_settings(AgentSettings()),
        "automation": _redact_settings(AutomationSettings()),
        "integrations": _redact_settings(IntegrationSettings()),
        "routing": _redact_settings(RoutingSettings()),
    }


@router.get("/paths")
def config_paths() -> list:
    paths = {
        "workflows": "./config/workflows",
        "automations": "./config/automations",
        "agents": "./config/agents",
        "skills": "./config/skills",
        "env": ".env",
        "knowledge_raw": str(KnowledgeSettings().knowledge_raw_dir),
        "knowledge_processed": str(KnowledgeSettings().knowledge_processed_dir),
        "knowledge_index": str(KnowledgeSettings().knowledge_index_dir),
    }
    return [
        {"key": key, "path": path, "exists": Path(path).expanduser().exists()}
        for key, path in paths.items()
    ]


@router.get("/version")
def version_info() -> dict:
    import importlib.metadata

    try:
        version = importlib.metadata.version("ai-os")
    except importlib.metadata.PackageNotFoundError:
        version = "1.2.0"
    return {"name": "ai-os", "version": version}


@router.get("/setup")
def setup_report() -> dict:
    return to_json(run_setup())


@router.post("/doctor", dependencies=[Depends(require_api_key)])
def system_doctor() -> dict:
    return to_json(run_full_check(include_benchmarks=False))
