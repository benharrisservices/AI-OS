"""Capability Layer CLI."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_os.capabilities.config import get_capability_settings
from ai_os.capabilities.registry import discover_skills, get_skill, list_skills

console = Console()


def register_capability_commands(app: typer.Typer) -> None:
    skill_app = typer.Typer(help="Capability skills", no_args_is_help=True)
    app.add_typer(skill_app, name="skill")

    @skill_app.command("list")
    def skill_list() -> None:
        """List available skills."""
        discover_skills()
        skills = list_skills()
        if not skills:
            console.print("[yellow]No skills registered[/yellow]")
            return
        table = Table(title="Skills")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Tools")
        table.add_column("Models")
        for skill in skills:
            table.add_row(
                skill.metadata.skill_id,
                skill.metadata.name,
                ", ".join(skill.metadata.required_tools) or "—",
                ", ".join(skill.metadata.required_models) or "—",
            )
        console.print(table)

    @skill_app.command("show")
    def skill_show(skill_id: str = typer.Argument(..., help="Skill ID")) -> None:
        """Show skill metadata and schemas."""
        discover_skills()
        skill = get_skill(skill_id)
        if skill is None:
            console.print(f"[red]Skill not found: {skill_id}[/red]")
            raise typer.Exit(1)
        meta = skill.metadata
        console.print(Panel.fit(
            f"[bold]{meta.name}[/bold] v{meta.version}\n\n"
            f"{meta.description}\n\n"
            f"Tools: {', '.join(meta.required_tools) or 'none'}\n"
            f"Models: {', '.join(meta.required_models) or 'any'}\n"
            f"Tags: {', '.join(meta.tags) or 'none'}",
            title=meta.skill_id,
        ))
        console.print("\n[dim]Input schema:[/dim]")
        console.print(json.dumps(meta.input_schema, indent=2))

    @skill_app.command("run")
    def skill_run(
        skill_id: str = typer.Argument(..., help="Skill ID to execute"),
        input_json: str | None = typer.Option(None, "--input", "-i", help="JSON input"),
    ) -> None:
        """Execute a skill directly."""
        discover_skills()
        skill = get_skill(skill_id)
        if skill is None:
            console.print(f"[red]Skill not found: {skill_id}[/red]")
            raise typer.Exit(1)
        input_data = json.loads(input_json) if input_json else {}
        output = skill.execute(input_data)
        color = "green" if output.success else "red"
        console.print(f"[{color}]{'OK' if output.success else 'FAILED'}[/{color}] confidence={output.confidence:.0%}")
        console.print(Panel.fit(output.summary or output.error or "Done", title=skill_id))
        if output.result:
            console.print(f"[dim]{json.dumps(output.result, indent=2, default=str)[:2000]}[/dim]")

    _ = get_capability_settings  # ensure settings module is referenced
