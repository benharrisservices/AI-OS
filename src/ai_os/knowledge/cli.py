"""AI-OS Knowledge Engine CLI."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ai_os.knowledge.config import get_settings
from ai_os.knowledge.models import SearchQuery
from ai_os.knowledge.pipeline import KnowledgePipeline
from ai_os.knowledge.search import HybridSearch

app = typer.Typer(help="AI-OS Knowledge Engine", no_args_is_help=True)
console = Console()


def _pipeline() -> KnowledgePipeline:
    return KnowledgePipeline(get_settings())


@app.command("ingest")
def ingest(
    path: Path = typer.Argument(..., help="File path or URL to ingest"),
    tag: list[str] = typer.Option([], "--tag", "-t", help="Tags to attach"),
) -> None:
    """Ingest a file or URL into the knowledge pipeline."""
    pipeline = _pipeline()
    target = str(path)
    if target.startswith("http://") or target.startswith("https://"):
        record = pipeline.ingest_url(target, tags=tag)
    else:
        record = pipeline.ingest_file(Path(target), tags=tag)
    console.print(f"[green]Ingested[/green] source_id={record.source_id} status={record.status.value}")


@app.command("process")
def process(
    source_id: str | None = typer.Option(None, help="Process a specific source"),
    all_pending: bool = typer.Option(False, "--all", help="Process all pending sources"),
) -> None:
    """Run preprocessing, chunking, embedding, and indexing."""
    pipeline = _pipeline()
    if source_id:
        document = pipeline.process_source(source_id)
        console.print(f"[green]Processed[/green] doc_id={document.doc_id} chunks={document.chunk_count}")
    elif all_pending:
        documents = pipeline.process_all_pending()
        console.print(f"[green]Processed[/green] {len(documents)} document(s)")
    else:
        raise typer.BadParameter("Provide --source-id or --all")


@app.command("reindex")
def reindex() -> None:
    """Rebuild vector and keyword indexes from processed artifacts."""
    pipeline = _pipeline()
    pipeline.reindex_all()
    console.print("[green]Reindex complete[/green]")


@app.command("search")
def search(
  query: str = typer.Argument(..., help="Search query"),
  top_k: int = typer.Option(10, help="Number of results"),
  mode: str = typer.Option("hybrid", help="hybrid | vector | keyword"),
) -> None:
    """Search the knowledge index."""
    settings = get_settings()
    engine = HybridSearch(settings)
    hits = engine.search(SearchQuery(query=query, mode=mode, top_k=top_k))

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


@app.command("status")
def status() -> None:
    """Show index manifest summary."""
    pipeline = _pipeline()
    manifest = pipeline.manifest.load()
    console.print(f"Documents: {manifest.document_count}")
    console.print(f"Chunks: {manifest.chunk_count}")
    console.print(f"Embedding model: {manifest.embedding_model}")
    console.print(f"Vector store: {manifest.vector_store}")
    console.print(f"Last incremental: {manifest.last_incremental_at}")


if __name__ == "__main__":
    app()
