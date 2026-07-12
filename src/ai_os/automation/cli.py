"""Automation Layer CLI commands."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from ai_os.automation.config import get_automation_settings
from ai_os.automation.models import TriggerType
from ai_os.automation.service import AutomationService

console = Console()


def register_automation_commands(app: typer.Typer) -> None:
    automation_app = typer.Typer(help="Automation management", no_args_is_help=True)
    app.add_typer(automation_app, name="automation")

    @automation_app.command("list")
    def automation_list() -> None:
        """List all automations."""
        automations = AutomationService(get_automation_settings()).list_automations()
        if not automations:
            console.print("[yellow]No automations defined[/yellow]")
            return
        table = Table(title="Automations")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Workflow")
        table.add_column("Trigger")
        table.add_column("Status")
        for auto in automations:
            table.add_row(
                auto.automation_id,
                auto.name,
                auto.workflow_id,
                auto.trigger.trigger_type.value,
                auto.status.value,
            )
        console.print(table)

    @automation_app.command("run")
    def automation_run(
        automation_id: str = typer.Argument(..., help="Automation ID to run"),
        input_json: str | None = typer.Option(None, "--input", "-i", help="JSON input override"),
        webhook_token: str | None = typer.Option(None, "--token", help="Webhook token"),
    ) -> None:
        """Run an automation immediately."""
        service = AutomationService(get_automation_settings())
        try:
            if webhook_token:
                record = service.trigger_webhook(automation_id, webhook_token)
            else:
                input_data = json.loads(input_json) if input_json else None
                record = service.run(
                    automation_id,
                    trigger_type=TriggerType.MANUAL,
                    input_override=input_data,
                )
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)

        color = "green" if record.status.value == "completed" else "red"
        console.print(f"[{color}]{record.status.value}[/{color}] execution_id={record.execution_id}")
        if record.task_id:
            console.print(f"  task_id={record.task_id}")
        console.print(f"  duration={record.duration_ms} ms · retries={record.retry_count}")
        if record.error:
            console.print(f"  [red]{record.error}[/red]")

    @automation_app.command("enable")
    def automation_enable(automation_id: str = typer.Argument(..., help="Automation ID")) -> None:
        """Enable an automation."""
        auto = AutomationService(get_automation_settings()).enable(automation_id)
        console.print(f"[green]Enabled[/green] {auto.automation_id}")

    @automation_app.command("disable")
    def automation_disable(automation_id: str = typer.Argument(..., help="Automation ID")) -> None:
        """Disable an automation."""
        auto = AutomationService(get_automation_settings()).disable(automation_id)
        console.print(f"[dim]Disabled[/dim] {auto.automation_id}")

    @automation_app.command("history")
    def automation_history(
        automation_id: str | None = typer.Argument(None, help="Filter by automation ID"),
        limit: int = typer.Option(20, "--limit", "-n"),
    ) -> None:
        """Show automation execution history."""
        records = AutomationService(get_automation_settings()).history(automation_id, limit=limit)
        if not records:
            console.print("[yellow]No execution history[/yellow]")
            return
        table = Table(title="Execution History")
        table.add_column("Execution")
        table.add_column("Automation")
        table.add_column("Status")
        table.add_column("Trigger")
        table.add_column("Duration", justify="right")
        table.add_column("Retries", justify="right")
        for rec in records:
            table.add_row(
                rec.execution_id,
                rec.automation_id,
                rec.status.value,
                rec.trigger_type.value,
                str(rec.duration_ms),
                str(rec.retry_count),
            )
        console.print(table)

    @automation_app.command("schedule")
    def automation_schedule(
        automation_id: str = typer.Argument(..., help="Automation ID"),
        cron: str | None = typer.Option(None, "--cron", help="Cron expression (5-field)"),
        interval: int | None = typer.Option(None, "--interval", help="Recurring interval in seconds"),
        delay: int | None = typer.Option(None, "--delay", help="Delay in seconds"),
        run_at: str | None = typer.Option(None, "--at", help="One-time ISO datetime"),
    ) -> None:
        """Configure schedule for an automation."""
        if not any([cron, interval, delay, run_at]):
            raise typer.BadParameter("Provide --cron, --interval, --delay, or --at")
        auto = AutomationService(get_automation_settings()).schedule(
            automation_id,
            cron=cron,
            interval_seconds=interval,
            delay_seconds=delay,
            run_at=run_at,
        )
        nxt = auto.next_run_at.isoformat() if auto.next_run_at else "none"
        console.print(f"[green]Scheduled[/green] {auto.automation_id} · next_run={nxt}")
