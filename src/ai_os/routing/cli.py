"""Model routing CLI."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from ai_os.routing.models import ModelRequest, RoutingPriority
from ai_os.routing.profiles import list_profiles
from ai_os.routing.router import ModelRouter

console = Console()


def register_routing_commands(app: typer.Typer) -> None:
    model_app = typer.Typer(help="Model routing", no_args_is_help=True)
    app.add_typer(model_app, name="model")

    @model_app.command("list")
    def model_list() -> None:
        """List available model profiles."""
        table = Table(title="Model Profiles")
        table.add_column("Provider")
        table.add_column("Model")
        table.add_column("Context", justify="right")
        table.add_column("Local")
        for p in list_profiles():
            table.add_row(p.provider_id, p.model_id, str(p.context_length), "yes" if p.is_local else "")
        console.print(table)

    @model_app.command("route")
    def model_route(
        task: str = typer.Argument("", help="Task description"),
        priority: list[str] = typer.Option([], "--priority", "-p"),
        provider: str | None = typer.Option(None, "--provider"),
        model: str | None = typer.Option(None, "--model"),
    ) -> None:
        """Route a task to the best available model."""
        priorities = []
        for p in priority:
            try:
                priorities.append(RoutingPriority(p))
            except ValueError:
                pass
        route = ModelRouter().route(
            ModelRequest(
                task=task,
                priorities=priorities,
                override_provider=provider,
                override_model=model,
            )
        )
        console.print(f"Provider: [bold]{route.provider_id}[/bold]")
        console.print(f"Model:    {route.model_id}")
        console.print(f"Score:    {route.score:.2f}")
        console.print(f"Fallback: {', '.join(route.fallback_chain)}")
