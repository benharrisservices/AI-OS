"""Integration CLI."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from ai_os.integrations.registry import discover_providers, get_provider, health_check_all, list_providers

console = Console()


def register_integration_commands(app: typer.Typer) -> None:
    provider_app = typer.Typer(help="External providers", no_args_is_help=True)
    app.add_typer(provider_app, name="provider")

    @provider_app.command("list")
    def provider_list() -> None:
        """List registered providers."""
        discover_providers()
        table = Table(title="Providers")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Configured")
        for p in list_providers():
            cfg = p.configure()
            table.add_row(p.provider_id, p.name, "yes" if cfg.enabled else "no")
        console.print(table)

    @provider_app.command("health")
    def provider_health() -> None:
        """Run health checks on all providers."""
        results = health_check_all()
        table = Table(title="Provider Health")
        table.add_column("Provider")
        table.add_column("Status")
        table.add_column("Latency", justify="right")
        table.add_column("Message")
        for h in results:
            color = {
                "healthy": "green",
                "not_configured": "dim",
                "missing_credentials": "yellow",
                "authentication_failed": "red",
                "network_error": "red",
                "disabled": "dim",
            }.get(h.status.value, "yellow")
            table.add_row(h.provider_id, f"[{color}]{h.status.value}[/{color}]", str(h.latency_ms), h.message[:40])
        console.print(table)

    @provider_app.command("capabilities")
    def provider_capabilities(provider_id: str = typer.Argument(...)) -> None:
        """List capabilities for a provider."""
        discover_providers()
        provider = get_provider(provider_id)
        if provider is None:
            console.print(f"[red]Unknown provider: {provider_id}[/red]")
            raise typer.Exit(1)
        for cap in provider.discover_capabilities():
            console.print(f"  {cap.name}: {cap.description}")
