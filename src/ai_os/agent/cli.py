"""Agent Runtime CLI commands."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from ai_os.agent.config import get_agent_settings
from ai_os.agent.engine import ExecutionEngine
from ai_os.agent.store import TaskStore
from ai_os.agent.tools import discover_tools, list_tools
from ai_os.agent.workflows import AgentLoader, WorkflowLoader

console = Console()


def register_agent_commands(app: typer.Typer) -> None:
    agent_app = typer.Typer(help="Agent management", no_args_is_help=True)
    workflow_app = typer.Typer(help="Workflow management", no_args_is_help=True)
    task_app = typer.Typer(help="Task management", no_args_is_help=True)

    app.add_typer(agent_app, name="agent")
    app.add_typer(workflow_app, name="workflow")
    app.add_typer(task_app, name="task")

    @agent_app.command("list")
    def agent_list() -> None:
        """List available agents."""
        settings = get_agent_settings()
        discover_tools(settings)
        agents = AgentLoader(settings).list_agents()
        tools = list_tools(enabled_only=True)

        table = Table(title="Agents")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Tools")
        for agent in agents:
            table.add_row(agent.agent_id, agent.name, ", ".join(agent.tools))
        console.print(table)
        console.print(f"\n[dim]{len(tools)} tool(s) registered[/dim]")

    @workflow_app.command("list")
    def workflow_list() -> None:
        """List available workflows."""
        workflows = WorkflowLoader(get_agent_settings()).list_workflows()
        if not workflows:
            console.print("[yellow]No workflows defined[/yellow]")
            return
        table = Table(title="Workflows")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Steps", justify="right")
        for wf in workflows:
            table.add_row(wf.workflow_id, wf.name, str(len(wf.steps)))
        console.print(table)

    @workflow_app.command("run")
    def workflow_run(
        workflow_id: str = typer.Argument(..., help="Workflow ID to execute"),
        input_json: str | None = typer.Option(None, "--input", "-i", help="JSON input parameters"),
    ) -> None:
        """Run a workflow by ID."""
        settings = get_agent_settings()
        input_data = json.loads(input_json) if input_json else {}
        engine = ExecutionEngine(settings)
        result = engine.run_workflow(workflow_id, input_data)

        color = "green" if result.status.value == "completed" else "red"
        console.print(f"[{color}]Workflow {result.status.value}[/{color}] task_id={result.task_id}")
        console.print(f"  Steps completed: {', '.join(result.steps_completed)}")
        console.print(f"  Duration: {result.duration_ms} ms")
        if result.error:
            console.print(f"  [red]Error: {result.error}[/red]")

    @task_app.command("status")
    def task_status(
        task_id: str = typer.Argument(..., help="Task ID"),
    ) -> None:
        """Show task status."""
        task = TaskStore(get_agent_settings()).get_task(task_id)
        if task is None:
            console.print(f"[red]Task not found: {task_id}[/red]")
            raise typer.Exit(1)
        console.print(f"Task: {task.task_id}")
        console.print(f"  Status: {task.status.value}")
        console.print(f"  Workflow: {task.workflow_id}")
        console.print(f"  Retries: {task.retry_count}/{task.max_retries}")
        if task.error:
            console.print(f"  Error: {task.error}")

    @task_app.command("logs")
    def task_logs(
        task_id: str = typer.Argument(..., help="Task ID"),
    ) -> None:
        """Show task execution logs."""
        store = TaskStore(get_agent_settings())
        logs = store.get_logs(task_id)
        if not logs:
            console.print("[yellow]No logs found[/yellow]")
            return
        for entry in logs:
            level = entry.get("level", "info")
            color = {"error": "red", "warning": "yellow"}.get(level, "dim")
            console.print(f"[{color}]{entry['timestamp']}[/{color}] {entry['message']}")
