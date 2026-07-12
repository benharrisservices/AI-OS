"""AI-OS Knowledge Engine CLI."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_os.knowledge.config import get_settings
from ai_os.knowledge.health import HealthService
from ai_os.knowledge.maintenance import MaintenanceService
from ai_os.knowledge.models import RetrievalQuery, SearchQuery
from ai_os.knowledge.pipeline import KnowledgePipeline
from ai_os.knowledge.purge import PurgeService
from ai_os.knowledge.retrieval import KnowledgeRetrieval, format_context_prompt
from ai_os.knowledge.search import HybridSearch
from ai_os.knowledge.watcher import InboxWatcher

app = typer.Typer(help="AI-OS — personal AI operating system", no_args_is_help=True)
maintenance_app = typer.Typer(help="Scheduled maintenance tasks", no_args_is_help=True)
app.add_typer(maintenance_app, name="maintenance")

console = Console()


def _pipeline() -> KnowledgePipeline:
    return KnowledgePipeline(get_settings())


def _format_bytes(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


@app.command("ingest")
def ingest(
    path: Path = typer.Argument(..., help="File path, directory, or URL to ingest"),
    tag: list[str] = typer.Option([], "--tag", "-t", help="Tags to attach"),
) -> None:
    """Ingest a file, directory, or URL into the knowledge pipeline."""
    pipeline = _pipeline()
    target = str(path)
    if target.startswith("http://") or target.startswith("https://"):
        record = pipeline.ingest_url(target, tags=tag)
        console.print(f"[green]Ingested[/green] source_id={record.source_id} status={record.status.value}")
        return

    resolved = Path(target)
    if resolved.is_dir():
        records = pipeline.ingest_directory(resolved, tags=tag)
        console.print(f"[green]Ingested[/green] {len(records)} file(s) from {resolved}")
        return

    record = pipeline.ingest_file(resolved, tags=tag)
    console.print(f"[green]Ingested[/green] source_id={record.source_id} status={record.status.value}")


@app.command("process")
def process(
    source_id: str | None = typer.Option(None, help="Process a specific source"),
    all_pending: bool = typer.Option(False, "--all", help="Process all pending sources"),
    force: bool = typer.Option(False, "--force", help="Reprocess even if fingerprint unchanged"),
) -> None:
    """Run preprocessing, chunking, embedding, and indexing."""
    pipeline = _pipeline()
    if source_id:
        document = pipeline.process_source(source_id, force=force)
        console.print(f"[green]Processed[/green] doc_id={document.doc_id} chunks={document.chunk_count}")
    elif all_pending:
        documents = pipeline.process_all_pending()
        console.print(f"[green]Processed[/green] {len(documents)} document(s)")
    else:
        raise typer.BadParameter("Provide --source-id or --all")


@app.command("purge")
def purge(
    source_id: str = typer.Argument(..., help="Source ID to purge"),
    delete_raw: bool = typer.Option(False, "--delete-raw", help="Also delete raw snapshot"),
) -> None:
    """Remove a source and all associated index entries."""
    PurgeService(get_settings()).purge_source(source_id, delete_raw=delete_raw)
    console.print(f"[green]Purged[/green] source_id={source_id}")


@app.command("reindex")
def reindex() -> None:
    """Rebuild vector and keyword indexes from processed artifacts."""
    _pipeline().reindex_all()
    console.print("[green]Reindex complete[/green]")


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(10, help="Number of results"),
    mode: str = typer.Option("hybrid", help="hybrid | vector | keyword"),
) -> None:
    """Search the knowledge index."""
    settings = get_settings()
    hits = HybridSearch(settings).search(SearchQuery(query=query, mode=mode, top_k=top_k))

    if not hits:
        console.print("[yellow]No results[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f'Results for "{query}"')
    table.add_column("Score", justify="right")
    table.add_column("Title")
    table.add_column("Section")
    table.add_column("Excerpt")

    for hit in hits:
        table.add_row(
            f"{hit.score:.4f}",
            hit.title,
            hit.heading_path,
            hit.excerpt.replace("\n", " ")[:120],
        )
    console.print(table)


@app.command("retrieve")
def retrieve(
    query: str = typer.Argument(..., help="Query to retrieve context for"),
    top_k: int = typer.Option(8, help="Chunks before deduplication"),
    mode: str = typer.Option("hybrid", help="hybrid | vector | keyword"),
    retrieval_mode: str = typer.Option("context", help="search | context | expand_parent"),
    max_tokens: int = typer.Option(4000, help="Context token budget"),
    max_chunks_per_doc: int = typer.Option(2, help="Diversity across documents"),
    show_prompt: bool = typer.Option(False, "--show-prompt", help="Print prompt-ready context"),
) -> None:
    """Assemble a citation-backed context bundle for RAG."""
    settings = get_settings()
    bundle = KnowledgeRetrieval(settings).retrieve(
        RetrievalQuery(
            query=query,
            top_k=top_k,
            mode=mode,
            retrieval_mode=retrieval_mode,
            max_tokens=max_tokens,
            max_chunks_per_doc=max_chunks_per_doc,
        )
    )

    if not bundle.chunks:
        console.print("[yellow]No context found[/yellow]")
        raise typer.Exit(0)

    if show_prompt:
        console.print(format_context_prompt(bundle))
        raise typer.Exit(0)

    console.print(
        f"[bold]{len(bundle.chunks)} chunk(s)[/bold] · "
        f"~{bundle.token_estimate} tokens · {bundle.retrieval_metadata.latency_ms} ms"
    )
    for citation, chunk in zip(bundle.citations, bundle.chunks, strict=True):
        console.print(
            f"\n[cyan]{citation.cite_key}[/cyan] [bold]{citation.title}[/bold] "
            f"([dim]{chunk.heading_path}[/dim]) score={chunk.score:.4f}"
        )
        console.print(f"  {chunk.text.replace(chr(10), ' ')[:280]}")
        console.print(f"  [dim]source: {citation.source_uri}[/dim]")


@app.command("status")
def status() -> None:
    """Show system health report (lightweight — use doctor for full integrity checks)."""
    report = HealthService(get_settings()).report(run_integrity=False)

    color = "green" if report.healthy else "yellow"
    console.print(Panel.fit(
        f"[bold]AI-OS[/bold]\n"
        f"Status: [{color}]{'healthy' if report.healthy else 'needs attention'}[/]",
        border_style=color,
    ))

    table = Table(title="Counts", show_header=True)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Sources", str(report.source_count))
    table.add_row("Documents", str(report.document_count))
    table.add_row("Chunks (child)", str(report.child_chunk_count))
    table.add_row("Embeddings", str(report.embedding_count))
    table.add_row("Vector index entries", str(report.vector_index_count))
    table.add_row("Keyword index entries", str(report.keyword_index_count))
    table.add_row("Storage", _format_bytes(report.storage_bytes))
    console.print(table)

    infra = Table(title="Infrastructure", show_header=True)
    infra.add_column("Setting")
    infra.add_column("Value")
    infra.add_row("Embedding provider", report.embedding_provider)
    infra.add_row("Embedding model", report.embedding_model)
    infra.add_row("Vector store", report.vector_store)
    infra.add_row("Ollama", "available" if report.ollama_available else "unavailable")
    infra.add_row("Last ingest", str(report.last_ingest_at or "never"))
    infra.add_row("Last reindex", str(report.last_reindex_at or "never"))
    console.print(infra)

    if report.warnings:
        console.print("\n[bold yellow]Warnings[/bold yellow]")
        for warning in report.warnings:
            console.print(f"  • {warning}")

    if report.recommendations:
        console.print("\n[bold cyan]Recommendations[/bold cyan]")
        for rec in report.recommendations:
            console.print(f"  → {rec}")

    if report.issues:
        console.print(f"\n[dim]{len(report.issues)} integrity issue(s) — run `ai-os doctor` for details[/dim]")


@app.command("doctor")
def doctor(
    repair: bool = typer.Option(False, "--repair", help="Automatically repair fixable issues"),
    full: bool = typer.Option(False, "--full", help="Run full system validation across all layers"),
    benchmark: bool = typer.Option(False, "--benchmark", help="Include performance benchmarks (with --full)"),
) -> None:
    """Validate index integrity and optionally repair. Use --full for system-wide checks."""
    if full:
        from ai_os.system_check import run_full_check

        report = run_full_check(include_benchmarks=benchmark)
        table = Table(title="AI-OS System Validation")
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Detail")
        table.add_column("ms", justify="right")
        for result in report.results:
            color = {"ok": "green", "warn": "yellow", "fail": "red"}.get(result.status, "white")
            table.add_row(result.name, f"[{color}]{result.status}[/{color}]", result.detail[:80], str(result.duration_ms))
        console.print(table)
        if report.healthy:
            console.print("\n[green]System validation passed[/green]")
        else:
            console.print("\n[red]System validation found failures[/red]")
            raise typer.Exit(code=1)
        return

    service = MaintenanceService(get_settings())
    issues, actions = service.doctor(repair=repair)

    if not issues:
        console.print("[green]No integrity issues found[/green]")
        return

    table = Table(title=f"Integrity issues ({len(issues)})")
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Message")
    for issue in issues:
        color = {"error": "red", "warning": "yellow", "info": "dim"}.get(issue.severity, "white")
        table.add_row(f"[{color}]{issue.severity}[/{color}]", issue.code, issue.message)
    console.print(table)

    if repair and actions:
        console.print("\n[green]Repair actions:[/green]")
        for action in actions:
            console.print(f"  • {action}")
    elif not repair:
        console.print("\n[dim]Run with --repair to fix repairable issues automatically[/dim]")


@app.command("import")
def import_cmd(
    source: str = typer.Argument(..., help="Path, GitHub owner/repo, or git URL"),
    source_type: str = typer.Option(
        "auto",
        "--type",
        "-t",
        help="Source type: auto, folder, markdown, text, pdf, docx, git, github, chats",
    ),
    tag: list[str] = typer.Option([], "--tag", help="Tags to attach"),
    clone: bool = typer.Option(False, "--clone", help="Clone remote git URL before import"),
) -> None:
    """Import content from files, folders, git repos, GitHub, or chat exports."""
    from ai_os.knowledge.populate import KnowledgeImporter

    importer = KnowledgeImporter(get_settings())

    def on_progress(msg: str) -> None:
        console.print(f"  {msg}")

    if clone or source.startswith("http") or source.startswith("git@"):
        progress = importer.clone_and_import(source, tags=tag or None, on_progress=on_progress)
    else:
        progress = importer.import_path(source, source_type=source_type, tags=tag or None, on_progress=on_progress)

    summary = progress.report()
    console.print(f"\n[bold]Import complete[/bold]: {summary}")
    if progress.errors:
        console.print("[yellow]Errors:[/yellow]")
        for err in progress.errors[:10]:
            console.print(f"  • {err}")
    if progress.failed:
        raise typer.Exit(code=1)

    from ai_os.knowledge.maintenance import MaintenanceService

    if MaintenanceService(get_settings()).ensure_search_indexes():
        console.print("[green]Search indexes rebuilt[/green]")


@app.command("update")
def update_cmd(
    check_only: bool = typer.Option(False, "--check", help="Verify installation without updating"),
) -> None:
    """Verify or refresh the AI-OS installation and dependencies."""
    import subprocess
    import sys

    console.print("[bold]Verifying AI-OS installation...[/bold]")
    from ai_os.system_check import run_full_check

    report = run_full_check()
    failed = [r for r in report.results if r.status == "fail"]
    if failed:
        for r in failed:
            console.print(f"  [red]✗[/red] {r.name}: {r.detail}")
    else:
        console.print("  [green]✓[/green] All system checks passed")

    if check_only:
        raise typer.Exit(code=1 if failed else 0)

    console.print("\n[bold]Syncing dependencies...[/bold]")
    result = subprocess.run(
        ["uv", "sync"],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]uv sync failed:[/red] {result.stderr or result.stdout}")
        raise typer.Exit(code=1)
    console.print(f"  [green]✓[/green] Dependencies synced (Python {sys.version_info.major}.{sys.version_info.minor})")


@app.command("setup")
def setup_cmd() -> None:
    """First-run setup: verify installation and recommend next steps."""
    from ai_os.setup import run_setup

    report = run_setup()
    console.print(Panel.fit("AI-OS Setup", border_style="blue"))

    for step in report.steps:
        icon = {"ok": "[green]✓[/green]", "warn": "[yellow]![/yellow]", "fail": "[red]✗[/red]"}.get(step.status, "?")
        console.print(f"  {icon} {step.message}")
        if step.next_action and step.status != "ok":
            console.print(f"      → {step.next_action}")

    console.print()
    if report.ready:
        console.print(f"[green]AI-OS is ready.[/green] Next: {report.recommended_next}")
    else:
        console.print(f"[red]Setup incomplete.[/red] {report.recommended_next}")
        raise typer.Exit(code=1)


onboarding_app = typer.Typer(help="Guided knowledge import onboarding", no_args_is_help=True)
app.add_typer(onboarding_app, name="onboarding")


@onboarding_app.callback(invoke_without_command=True)
def onboarding_main(ctx: typer.Context) -> None:
    """Show recommended import order and presets."""
    if ctx.invoked_subcommand is not None:
        return
    from ai_os.knowledge.onboarding import load_presets

    presets = load_presets()
    console.print(Panel.fit(
        "Import your knowledge in the recommended order.\n"
        "Nothing is imported automatically — you choose each path.",
        title="Knowledge Onboarding",
        border_style="cyan",
    ))
    table = Table(title="Recommended import order")
    table.add_column("#", justify="right")
    table.add_column("Preset")
    table.add_column("Type")
    table.add_column("Suggested path")
    for p in presets:
        table.add_row(str(p.order), p.id, p.source_type, p.suggested_path)
    console.print(table)
    console.print("\n[dim]Validate before importing:[/dim]")
    console.print("  ai-os onboarding validate ai-os-repo ./docs")
    console.print("  ai-os onboarding import ai-os-repo ./docs --yes")


@onboarding_app.command("validate")
def onboarding_validate(
    preset_id: str = typer.Argument(..., help="Preset ID (e.g. ai-os-repo)"),
    path: str = typer.Argument(..., help="Path to your files or folder"),
) -> None:
    """Validate an import without executing it."""
    from ai_os.knowledge.onboarding import format_bytes, validate_import

    try:
        result = validate_import(preset_id, path)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]{result.preset.name}[/bold] — {result.source_path}")
    console.print(f"  Files found:     {result.total_files}")
    console.print(f"  New:             {result.new_files}")
    console.print(f"  Duplicates:      {result.duplicate_files}")
    console.print(f"  Unsupported:     {result.unsupported_files}")
    console.print(f"  Total size:      {format_bytes(result.total_bytes)}")
    console.print(f"  Est. time:       ~{result.estimated_minutes} min ({result.estimated_seconds:.0f}s)")

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for err in result.errors[:10]:
            console.print(f"  • {err}")

    if result.ready:
        console.print("\n[green]Ready to import.[/green] Run:")
        console.print(f"  uv run ai-os onboarding import {preset_id} {path} --yes")
    elif result.duplicate_files == result.total_files and result.total_files > 0:
        console.print("\n[yellow]All files already imported — nothing new to add.[/yellow]")
    else:
        console.print("\n[red]Not ready to import.[/red] Fix errors above.")
        raise typer.Exit(code=1)


@onboarding_app.command("import")
def onboarding_import(
    preset_id: str = typer.Argument(..., help="Preset ID"),
    path: str = typer.Argument(..., help="Path to import"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm import execution"),
    tag: list[str] = typer.Option([], "--tag", help="Extra tags"),
) -> None:
    """Import using a preset (requires --yes after validation)."""
    from ai_os.knowledge.onboarding import validate_import
    from ai_os.knowledge.populate import KnowledgeImporter

    if not yes:
        console.print("[red]Import not started.[/red] Validate first, then add --yes to confirm.")
        console.print(f"  ai-os onboarding validate {preset_id} {path}")
        raise typer.Exit(code=1)

    result = validate_import(preset_id, path)
    if not result.ready:
        console.print("[red]Validation failed.[/red] Run validate first.")
        raise typer.Exit(code=1)

    tags = list(result.preset.tags) + list(tag)
    importer = KnowledgeImporter(get_settings())

    def on_progress(msg: str) -> None:
        console.print(f"  {msg}")

    console.print(f"\n[bold]Importing {result.new_files} file(s)...[/bold]")
    progress = importer.import_path(path, source_type=result.preset.source_type, tags=tags, on_progress=on_progress)
    summary = progress.report()

    from ai_os.knowledge.maintenance import MaintenanceService

    if MaintenanceService(get_settings()).ensure_search_indexes():
        console.print("  [dim]Rebuilt search indexes[/dim]")

    console.print(f"\n[green]Done:[/green] {summary}")
    console.print("[dim]Try: uv run ai-os search \"your topic\"[/dim]")


@app.command("watch")
def watch(
    once: bool = typer.Option(False, "--once", help="Process inbox once and exit"),
) -> None:
    """Watch the inbox directory and auto-ingest new or modified files."""
    settings = get_settings()
    watcher = InboxWatcher(settings)
    if once:
        count = watcher.run_once()
        console.print(f"[green]Processed[/green] {count} file(s) from {settings.knowledge_watch_dir}")
        return
    console.print(f"Watching {settings.knowledge_watch_dir} (Ctrl+C to stop)...")
    watcher.watch_forever()


@app.command("backup")
def backup(
    output: Path | None = typer.Option(None, "--output", "-o", help="Backup file path"),
    verify: bool = typer.Option(False, "--verify", help="Verify latest or specified backup"),
) -> None:
    """Create or verify a compressed backup of knowledge directories."""
    service = MaintenanceService(get_settings())
    if verify:
        ok, msg = service.verify_backup(output)
        if ok:
            console.print(f"[green]{msg}[/green]")
        else:
            console.print(f"[red]{msg}[/red]")
            raise typer.Exit(code=1)
        return
    dest = service.backup(output)
    console.print(f"[green]Backup created[/green] {dest}")
    ok, msg = service.verify_backup(dest)
    if ok:
        console.print(f"[dim]{msg}[/dim]")
    else:
        console.print(f"[yellow]Warning:[/yellow] {msg}")


@maintenance_app.command("ingest")
def maintenance_ingest() -> None:
    """Ingest all files in the watch inbox."""
    count = MaintenanceService(get_settings()).ingest_inbox()
    console.print(f"[green]Ingested[/green] {count} file(s)")


@maintenance_app.command("reindex")
def maintenance_reindex() -> None:
    """Rebuild all indexes from processed artifacts."""
    MaintenanceService(get_settings()).reindex()
    console.print("[green]Reindex complete[/green]")


@maintenance_app.command("cleanup")
def maintenance_cleanup() -> None:
    """Purge orphans and stale cache files."""
    actions = MaintenanceService(get_settings()).cleanup()
    if actions:
        for action in actions:
            console.print(f"  • {action}")
    else:
        console.print("[green]Nothing to clean up[/green]")


@maintenance_app.command("doctor")
def maintenance_doctor(
    repair: bool = typer.Option(True, "--repair/--no-repair", help="Auto-repair fixable issues"),
) -> None:
    """Run integrity checks."""
    issues, actions = MaintenanceService(get_settings()).doctor(repair=repair)
    console.print(f"Found {len(issues)} issue(s), {len(actions)} repair action(s)")


@maintenance_app.command("backup")
def maintenance_backup() -> None:
    """Create a knowledge backup."""
    dest = MaintenanceService(get_settings()).backup()
    console.print(f"[green]Backup created[/green] {dest}")


@maintenance_app.command("run")
def maintenance_run() -> None:
    """Run the full maintenance cycle."""
    results = MaintenanceService(get_settings()).run_all()
    for key, value in results.items():
        console.print(f"  {key}: {value}")


if __name__ == "__main__":
    app()
