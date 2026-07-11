"""Memory System CLI commands."""

from __future__ import annotations

import json
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_os.memory.config import get_memory_settings
from ai_os.memory.manager import MemoryManager
from ai_os.memory.models import (
    MemorySearchQuery,
    MemoryType,
    PromotionPolicy,
    PromotionRequest,
    PromotionTarget,
)

console = Console()


def register_memory_commands(app: typer.Typer) -> None:
    memory_app = typer.Typer(help="Memory management", no_args_is_help=True)
    app.add_typer(memory_app, name="memory")

    @memory_app.command("list")
    def memory_list(
        memory_type: str | None = typer.Option(None, "--type", "-t", help="Filter by memory type"),
        include_archived: bool = typer.Option(False, "--archived", help="Include archived memories"),
    ) -> None:
        """List stored memories."""
        manager = MemoryManager(get_memory_settings())
        if memory_type:
            try:
                mtype = MemoryType(memory_type)
            except ValueError:
                valid = ", ".join(t.value for t in MemoryType)
                raise typer.BadParameter(f"Unknown type '{memory_type}'. Choose from: {valid}")
            from ai_os.memory.models import MemoryStatus

            status = None if include_archived else MemoryStatus.ACTIVE
            records = manager.list_by_type(mtype, status=status)
        else:
            from ai_os.memory.models import MemoryStatus

            status = None if include_archived else MemoryStatus.ACTIVE
            records = manager.list_all(status=status)

        if not records:
            console.print("[yellow]No memories found[/yellow]")
            return

        table = Table(title="Memories")
        table.add_column("ID")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Summary")
        table.add_column("Created")

        for record in records[:30]:
            summary = _record_summary(record)
            table.add_row(
                record.memory_id,
                record.memory_type.value,
                record.status.value,
                summary[:60],
                record.created_at.strftime("%Y-%m-%d %H:%M"),
            )
        console.print(table)

    @memory_app.command("search")
    def memory_search(
        query: str = typer.Argument(..., help="Search text"),
        memory_type: str | None = typer.Option(None, "--type", "-t"),
        since: str | None = typer.Option(None, "--since", help="ISO date lower bound"),
        limit: int = typer.Option(10, "--limit", "-n"),
    ) -> None:
        """Search memories by text and time."""
        manager = MemoryManager(get_memory_settings())
        types = []
        if memory_type:
            types = [MemoryType(memory_type)]
        search = MemorySearchQuery(
            query=query,
            memory_types=types,
            since=datetime.fromisoformat(since) if since else None,
            limit=limit,
        )
        results = manager.search(search)
        if not results:
            console.print("[yellow]No matches[/yellow]")
            return
        for record in results:
            console.print(f"[bold]{record.memory_id}[/bold] [{record.memory_type.value}] {_record_summary(record)}")

    @memory_app.command("show")
    def memory_show(memory_id: str = typer.Argument(..., help="Memory ID")) -> None:
        """Show a single memory record."""
        record = MemoryManager(get_memory_settings()).get(memory_id)
        if record is None:
            console.print(f"[red]Memory not found: {memory_id}[/red]")
            raise typer.Exit(1)
        console.print(Panel.fit(
            json.dumps(record.model_dump(mode="json"), indent=2, default=str),
            title=f"{record.memory_type.value} · {record.memory_id}",
        ))

    @memory_app.command("promote")
    def memory_promote(
        memory_id: str = typer.Argument(..., help="Source memory ID"),
        to: str = typer.Option(..., "--to", help="Target tier: episodic or semantic"),
        approve: bool = typer.Option(False, "--approve", help="Explicit approval (required for semantic)"),
        concept: str | None = typer.Option(None, "--concept", help="Semantic concept label"),
        abstraction: str | None = typer.Option(None, "--abstraction", help="Semantic abstraction text"),
    ) -> None:
        """Promote memory between tiers (Working → Episodic → Semantic)."""
        try:
            target = PromotionTarget(to)
        except ValueError:
            raise typer.BadParameter("Target must be 'episodic' or 'semantic'")

        policy = (
            PromotionPolicy.MANUAL_APPROVAL
            if target == PromotionTarget.SEMANTIC or approve
            else PromotionPolicy.WORKFLOW_COMPLETION
        )
        result = MemoryManager(get_memory_settings()).promote(
            PromotionRequest(
                source_memory_id=memory_id,
                target_type=target,
                policy=policy,
                approved=approve or target == PromotionTarget.EPISODIC and policy == PromotionPolicy.WORKFLOW_COMPLETION,
                concept=concept,
                abstraction=abstraction,
                approved_by="cli" if approve else None,
            )
        )
        if result.success:
            console.print(f"[green]Promoted[/green] {memory_id} → {result.target_memory_id}")
        else:
            console.print(f"[red]Promotion failed:[/red] {result.error}")
            raise typer.Exit(1)

    @memory_app.command("archive")
    def memory_archive(memory_id: str = typer.Argument(..., help="Memory ID to archive")) -> None:
        """Archive a memory record."""
        record = MemoryManager(get_memory_settings()).archive(memory_id)
        console.print(f"[green]Archived[/green] {record.memory_id} ({record.memory_type.value})")

    @memory_app.command("expire")
    def memory_expire() -> None:
        """Expire overdue working memories."""
        expired = MemoryManager(get_memory_settings()).expire_working()
        if expired:
            console.print(f"[green]Expired {len(expired)} working memory record(s)[/green]")
        else:
            console.print("[dim]No working memories to expire[/dim]")


def _record_summary(record) -> str:
    for attr in ("summary", "abstraction", "title", "procedure_name", "scope"):
        value = getattr(record, attr, None)
        if value:
            return str(value)
    return record.memory_type.value
