"""First-run setup — reuses system_check, plain-English guidance."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from ai_os.integrations.registry import discover_providers, health_check_all
from ai_os.knowledge.config import KnowledgeSettings
from ai_os.system_check import run_full_check, CheckResult


@dataclass
class SetupStep:
    name: str
    status: str  # ok, warn, fail
    message: str
    next_action: str = ""


@dataclass
class SetupReport:
    steps: list[SetupStep] = field(default_factory=list)
    ready: bool = True
    recommended_next: str = ""

    def add(self, step: SetupStep) -> None:
        self.steps.append(step)
        if step.status == "fail":
            self.ready = False


def _check_writable_dirs() -> SetupStep:
    dirs = [
        Path("./memory"),
        Path("./knowledge/raw"),
        Path("./knowledge/processed"),
        Path("./knowledge/index"),
    ]
    failed = []
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        test_file = d / ".write-test"
        try:
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
        except OSError:
            failed.append(str(d))
    if failed:
        return SetupStep(
            name="writable_directories",
            status="fail",
            message=f"Cannot write to: {', '.join(failed)}",
            next_action="Check folder permissions or choose a different install location.",
        )
    return SetupStep(
        name="writable_directories",
        status="ok",
        message="Memory and knowledge folders are writable.",
    )


def _check_env_file() -> SetupStep:
    if Path(".env").exists():
        return SetupStep(name="configuration", status="ok", message="Found .env configuration file.")
    if Path(".env.example").exists():
        return SetupStep(
            name="configuration",
            status="warn",
            message="No .env file yet. Example configuration is available.",
            next_action="Run: cp .env.example .env  then add your API keys.",
        )
    return SetupStep(
        name="configuration",
        status="warn",
        message="No .env file found.",
        next_action="Copy config/personal/providers.env.example into .env and add credentials.",
    )


def _check_ollama_models() -> SetupStep:
    settings = KnowledgeSettings()
    host = os.environ.get("OLLAMA_HOST", settings.ollama_host).rstrip("/")
    embed_model = settings.embedding_model
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{host}/api/tags")
            if response.status_code != 200:
                return SetupStep(
                    name="ollama_models",
                    status="fail",
                    message=f"Ollama is not responding at {host}.",
                    next_action="Install Ollama from https://ollama.com and run: ollama serve",
                )
            models = [m.get("name", "") for m in response.json().get("models", [])]
    except Exception:
        return SetupStep(
            name="ollama_models",
            status="fail",
            message="Ollama is not running.",
            next_action="Install Ollama, then run: ollama pull nomic-embed-text",
        )

    has_embed = any(embed_model in name for name in models)
    if not has_embed:
        return SetupStep(
            name="ollama_models",
            status="fail",
            message=f"Embedding model '{embed_model}' is not installed.",
            next_action=f"Run: ollama pull {embed_model}",
        )
    return SetupStep(
        name="ollama_models",
        status="ok",
        message=f"Ollama is running with embedding model '{embed_model}'.",
    )


def _check_providers_plain() -> SetupStep:
    discover_providers()
    health = health_check_all()
    healthy = sum(1 for h in health if h.status.value == "healthy")
    optional = sum(1 for h in health if h.status.value == "not_configured")
    degraded = sum(1 for h in health if h.status.value not in ("healthy", "not_configured"))
    if degraded:
        return SetupStep(
            name="providers",
            status="warn",
            message=f"Providers: {healthy} connected, {degraded} need attention, {optional} optional.",
            next_action="Run: uv run ai-os provider health",
        )
    return SetupStep(
        name="providers",
        status="ok",
        message=f"Providers: {healthy} connected, {optional} optional not configured.",
    )


def _map_system_check(result: CheckResult) -> SetupStep:
    messages = {
        "python_version": ("Python version", "Install Python 3.12 or newer."),
        "dependencies": ("Python packages", "Run: uv sync"),
        "knowledge_engine": ("Knowledge engine", "Run: ai-os doctor"),
        "ollama_models": ("Ollama", "Run: ollama pull nomic-embed-text"),
    }
    label, action = messages.get(result.name, (result.name, "Run: ai-os doctor --full"))
    if result.status == "ok":
        return SetupStep(name=result.name, status="ok", message=f"{label}: {result.detail}")
    return SetupStep(name=result.name, status="fail", message=f"{label} failed: {result.detail}", next_action=action)


def run_setup() -> SetupReport:
    """Run first-time setup checks. Reuses system_check where possible."""
    report = SetupReport()

    if sys.version_info < (3, 12):
        report.add(SetupStep(
            name="python_version",
            status="fail",
            message=f"Python 3.12+ required (found {sys.version_info.major}.{sys.version_info.minor}).",
            next_action="Install Python 3.12 from https://python.org",
        ))
        report.recommended_next = "Install Python 3.12, then run ai-os setup again."
        return report

    report.add(SetupStep(
        name="python_version",
        status="ok",
        message=f"Python {sys.version_info.major}.{sys.version_info.minor} is supported.",
    ))

    system = run_full_check(include_benchmarks=False)
    for result in system.results:
        if result.name in ("backup_verification", "integrations", "model_router"):
            continue
        step = _map_system_check(result)
        report.add(step)

    report.add(_check_writable_dirs())
    report.add(_check_env_file())
    report.add(_check_ollama_models())
    report.add(_check_providers_plain())

    if not report.ready:
        failed = [s for s in report.steps if s.status == "fail"]
        report.recommended_next = failed[0].next_action or "Run: uv run ai-os doctor --full"
    elif any(s.status == "warn" for s in report.steps):
        report.recommended_next = "Run: uv run ai-os onboarding  to import your knowledge."
    else:
        report.recommended_next = "Run: uv run ai-os onboarding  then uv run ai-os workflow run morning-briefing -f config/personal/workflows/morning-briefing.json"

    return report
