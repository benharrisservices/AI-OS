"""Decision Engine CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_os.decision.config import get_decision_settings
from ai_os.decision.models import DecisionRequest, ReasoningStrategyName
from ai_os.decision.pipeline import DecisionPipeline
from ai_os.decision.store import DecisionStore

console = Console()


def register_decision_commands(app: typer.Typer) -> None:
    """Attach decision commands to the root AI-OS CLI."""

    @app.command("decide")
    def decide(
        question: str = typer.Argument(..., help="Decision question to reason about"),
        strategy: str = typer.Option("analytical", "--strategy", "-s", help="Reasoning strategy"),
        context: str | None = typer.Option(None, "--context", "-c", help="Additional context"),
        constraint: list[str] = typer.Option([], "--constraint", help="Constraint to apply"),
        option: list[str] = typer.Option([], "--option", help="Suggested option"),
        no_knowledge: bool = typer.Option(False, "--no-knowledge", help="Skip knowledge retrieval"),
    ) -> None:
        """Run the decision pipeline on a question."""
        try:
            strategy_enum = ReasoningStrategyName(strategy)
        except ValueError:
            valid = ", ".join(s.value for s in ReasoningStrategyName)
            raise typer.BadParameter(f"Unknown strategy '{strategy}'. Choose from: {valid}")

        request = DecisionRequest(
            question=question,
            strategy=strategy_enum,
            context=context,
            user_constraints=constraint,
            option_hints=option,
            require_knowledge=not no_knowledge,
        )
        result = DecisionPipeline(get_decision_settings()).decide(request)

        if result.recommendation:
            console.print(Panel.fit(
                f"[bold]{result.recommendation.title}[/bold]\n\n"
                f"{result.recommendation.summary}\n\n"
                f"[dim]Confidence: {result.confidence:.0%} · Strategy: {result.strategy.value}[/dim]",
                title="Recommendation",
                border_style="green",
            ))
        console.print(f"[dim]decision_id={result.decision_id} · evidence={len(result.evidence)} · options={len(result.options)}[/dim]")

    @app.command("decisions")
    def decisions() -> None:
        """List all recorded decisions."""
        records = DecisionStore(get_decision_settings()).list_all()
        if not records:
            console.print("[yellow]No decisions recorded[/yellow]")
            return

        table = Table(title="Decisions")
        table.add_column("ID")
        table.add_column("Question")
        table.add_column("Strategy")
        table.add_column("Confidence", justify="right")
        table.add_column("Created")

        for record in records[:20]:
            table.add_row(
                record.decision_id,
                record.request.question[:50],
                record.strategy.value,
                f"{record.confidence:.0%}",
                record.created_at.strftime("%Y-%m-%d %H:%M"),
            )
        console.print(table)

    @app.command("decision")
    def decision_show(
        decision_id: str = typer.Argument(..., help="Decision ID to inspect"),
    ) -> None:
        """Show full details of a recorded decision."""
        record = DecisionStore(get_decision_settings()).get(decision_id)
        if record is None:
            console.print(f"[red]Decision not found: {decision_id}[/red]")
            raise typer.Exit(1)

        console.print(Panel.fit(f"[bold]{record.request.question}[/bold]", title=record.decision_id))

        if record.recommendation:
            console.print(f"\n[green]Recommendation:[/green] {record.recommendation.title}")
            console.print(f"  {record.recommendation.rationale}")
            console.print(f"  Confidence: {record.confidence:.0%}")

        if record.evidence:
            console.print(f"\n[bold]Evidence ({len(record.evidence)})[/bold]")
            for ev in record.evidence:
                console.print(f"  {ev.cite_key} {ev.title}: {ev.content[:100]}...")

        if record.options:
            console.print(f"\n[bold]Options ({len(record.options)})[/bold]")
            for opt in record.options:
                score = f"{opt.score:.2f}" if opt.score is not None else "—"
                console.print(f"  [{score}] {opt.title}: {opt.description[:80]}")

        if record.risks:
            console.print(f"\n[bold]Risks ({len(record.risks)})[/bold]")
            for risk in record.risks:
                console.print(f"  [{risk.severity.value}] {risk.description}")

        console.print(f"\n[dim]Trace: {len(record.reasoning_trace)} pipeline stages[/dim]")
