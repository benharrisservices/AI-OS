"""API startup: logging, data-dir defaults, environment checklist."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from ai_os.env_registry import evaluate_env
from ai_os.integrations.registry import discover_providers, health_check_all
from ai_os.integrations.models import ProviderStatus
from ai_os.knowledge.config import KnowledgeSettings

logger = logging.getLogger("ai_os.api")


def configure_logging() -> None:
    level_name = os.environ.get("AI_OS_LOG_LEVEL", "info").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def apply_data_dir_defaults() -> None:
    """When AI_OS_DATA_DIR is set, derive knowledge paths under it unless overridden."""
    data_dir = os.environ.get("AI_OS_DATA_DIR", "").strip()
    if not data_dir:
        return
    root = data_dir.rstrip("/")
    defaults = {
        "KNOWLEDGE_RAW_DIR": f"{root}/knowledge/raw",
        "KNOWLEDGE_PROCESSED_DIR": f"{root}/knowledge/processed",
        "KNOWLEDGE_INDEX_DIR": f"{root}/knowledge/index",
        "VECTOR_STORE_PATH": f"{root}/knowledge/index/vectors",
        "KNOWLEDGE_WATCH_DIR": f"{root}/knowledge/raw/inbox",
        "KNOWLEDGE_BACKUP_DIR": f"{root}/knowledge/backups",
        "MEMORY_WORKING_DIR": f"{root}/memory/working",
        "MEMORY_EPISODIC_DIR": f"{root}/memory/episodic",
        "MEMORY_SEMANTIC_DIR": f"{root}/memory/semantic",
        "MEMORY_PROCEDURAL_DIR": f"{root}/memory/procedural",
    }
    for key, value in defaults.items():
        if not os.environ.get(key, "").strip():
            os.environ[key] = value


def _status_icon(healthy: bool, configured: bool, status: ProviderStatus | None = None) -> str:
    if status == ProviderStatus.HEALTHY:
        return "✓"
    if status in (ProviderStatus.AUTHENTICATION_FAILED, ProviderStatus.NETWORK_ERROR):
        return "✗"
    if configured:
        return "⚠"
    return "⚠"


def print_startup_checklist(port: int) -> None:
    """Print a clean startup checklist to stdout (never raises)."""
    env_report = evaluate_env()
    discover_providers()
    health_results = {h.provider_id: h for h in health_check_all()}

    lines: list[str] = []
    lines.append("")
    lines.append("sedr API — startup")
    lines.append("─" * 40)

    # Provider lines from env registry + live health when configured.
    for p in env_report.providers:
        health = health_results.get(p.provider_id)
        if health and health.status == ProviderStatus.HEALTHY:
            lines.append(f"  ✓ {p.display_name}")
        elif health and health.status == ProviderStatus.DISABLED:
            lines.append(f"  – {p.display_name} (disabled)")
        elif health and health.status == ProviderStatus.AUTHENTICATION_FAILED:
            lines.append(f"  ✗ {p.display_name} (authentication failed)")
        elif health and health.status == ProviderStatus.NETWORK_ERROR:
            lines.append(f"  ✗ {p.display_name} (network error)")
        elif health and health.status == ProviderStatus.MISSING_CREDENTIALS:
            lines.append(f"  ⚠ {p.display_name} (missing credentials)")
        elif p.configured:
            lines.append(f"  ⚠ {p.display_name} ({health.message if health else p.message})")
        else:
            lines.append(f"  ⚠ {p.display_name} not configured")

    # Knowledge summary.
    try:
        settings = KnowledgeSettings()
        settings.ensure_dirs()
        from ai_os.knowledge.health import HealthService

        kh = HealthService(settings).report(run_integrity=False)
        lines.append(f"  ✓ Knowledge loaded ({kh.document_count} docs, {kh.chunk_count} chunks)")
    except Exception as exc:
        lines.append(f"  ⚠ Knowledge ({exc})")

    lines.append(f"  ✓ API started")
    lines.append(f"  ✓ Listening on :{port}")
    lines.append("─" * 40)
    lines.append("")

    banner = "\n".join(lines)
    print(banner, flush=True)
    logger.info("Startup checklist complete (port=%s)", port)


@asynccontextmanager
async def lifespan(_app: object) -> AsyncIterator[None]:
    configure_logging()
    apply_data_dir_defaults()
    port = int(os.environ.get("PORT", "8741"))
    print_startup_checklist(port)
    logger.info("sedr API ready")
    yield
    logger.info("sedr API shutting down gracefully")
