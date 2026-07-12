"""User experience CLI extensions."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_os.automation.config import get_automation_settings
from ai_os.automation.service import AutomationService
from ai_os.capabilities.registry import discover_skills, list_skills
from ai_os.integrations.registry import health_check_all
from ai_os.memory.intelligence import MemoryIntelligence
from ai_os.memory.manager import MemoryManager
from ai_os.routing.router import ModelRouter
from ai_os.routing.models import ModelRequest

console = Console()


def register_ux_commands(app: typer.Typer) -> None:
    @app.command("dashboard")
    def dashboard() -> None:
        """System overview dashboard."""
        discover_skills()
        skills = list_skills()
        automations = AutomationService(get_automation_settings()).list_automations()
        memories = MemoryManager().list_all(status=None)
        providers = health_check_all()
        healthy = sum(1 for p in providers if p.status.value == "healthy")

        console.print(Panel.fit(
            f"Skills: {len(skills)} · Automations: {len(automations)}\n"
            f"Memories: {len(memories)} · Providers healthy: {healthy}/{len(providers)}",
            title="AI-OS Dashboard",
            border_style="blue",
        ))

    @app.command("timeline")
    def timeline(
        query: str = typer.Option("", "--query", "-q"),
        limit: int = typer.Option(20, "--limit", "-n"),
    ) -> None:
        """Activity timeline from episodic memory."""
        events = MemoryIntelligence().build_timeline(query=query, limit=limit)
        if not events:
            console.print("[yellow]No timeline events[/yellow]")
            return
        for event in events:
            console.print(f"[dim]{event['occurred_at']}[/dim] [{event['event_type']}] {event['title']}")

    @app.command("diagnostics")
    def diagnostics() -> None:
        """System diagnostics."""
        checks = []
        try:
            discover_skills()
            checks.append(("Skills", "ok", str(len(list_skills()))))
        except Exception as exc:
            checks.append(("Skills", "fail", str(exc)))
        try:
            health_check_all()
            checks.append(("Providers", "ok", "registered"))
        except Exception as exc:
            checks.append(("Providers", "fail", str(exc)))
        try:
            route = ModelRouter().route(ModelRequest(task="health"))
            checks.append(("Model router", "ok", route.provider_id))
        except Exception as exc:
            checks.append(("Model router", "fail", str(exc)))

        table = Table(title="Diagnostics")
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Detail")
        for name, status, detail in checks:
            color = "green" if status == "ok" else "red"
            table.add_row(name, f"[{color}]{status}[/{color}]", detail)
        console.print(table)

    @app.command("explore")
    def explore_memory(
        query: str = typer.Argument("", help="Search query"),
        limit: int = typer.Option(10, "--limit", "-n"),
    ) -> None:
        """Searchable memory explorer."""
        from ai_os.memory.models import MemorySearchQuery

        records = MemoryManager().search(MemorySearchQuery(query=query, limit=limit))
        if not records:
            console.print("[yellow]No memories found[/yellow]")
            return
        for r in records:
            summary = getattr(r, "summary", None) or getattr(r, "abstraction", None) or getattr(r, "title", r.memory_id)
            console.print(f"[bold]{r.memory_id}[/bold] [{r.memory_type.value}] {summary}")

    @app.command("activity")
    def activity(limit: int = typer.Option(20, "--limit", "-n")) -> None:
        """Recent execution activity across automations."""
        records = AutomationService(get_automation_settings()).history(limit=limit)
        if not records:
            console.print("[yellow]No activity[/yellow]")
            return
        table = Table(title="Recent Activity")
        table.add_column("Time")
        table.add_column("Automation")
        table.add_column("Status")
        table.add_column("Duration", justify="right")
        for r in records:
            ts = r.started_at.strftime("%m-%d %H:%M") if r.started_at else "—"
            table.add_row(ts, r.automation_id, r.status.value, str(r.duration_ms))
        console.print(table)

    @app.command("config-show")
    def config_show() -> None:
        """Show configuration paths."""
        paths = {
            "workflows": "./config/workflows",
            "automations": "./config/automations",
            "agents": "./config/agents",
            "skills": "./config/skills",
            "env": ".env",
        }
        for key, path in paths.items():
            exists = Path(path).exists()
            console.print(f"  {key}: {path} [{'exists' if exists else 'missing'}]")

    @app.command("memory-insights")
    def memory_insights() -> None:
        """Memory intelligence summary."""
        intel = MemoryIntelligence()
        dupes = intel.detect_duplicates()
        clusters = intel.cluster_semantic()
        contradictions = intel.detect_contradictions()
        promotions = intel.promotion_recommendations()
        console.print(Panel.fit(
            f"Duplicates: {len(dupes)} groups\n"
            f"Semantic clusters: {len(clusters)}\n"
            f"Contradictions: {len(contradictions)}\n"
            f"Promotion candidates: {len(promotions)}",
            title="Memory Intelligence",
        ))

    @app.command("benchmark")
    def benchmark_cmd() -> None:
        """Run performance benchmarks for startup diagnostics."""
        from ai_os.system_check import run_benchmarks

        results = run_benchmarks()
        table = Table(title="AI-OS Benchmarks")
        table.add_column("Operation")
        table.add_column("Status")
        table.add_column("Latency", justify="right")
        for result in results:
            color = "green" if result.status == "ok" else "red"
            table.add_row(result.name, f"[{color}]{result.status}[/{color}]", result.detail)
        console.print(table)
