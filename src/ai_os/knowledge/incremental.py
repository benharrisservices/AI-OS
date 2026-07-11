"""Incremental indexing: diff chunks and reuse unchanged embeddings."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_os.knowledge.ids import content_hash
from ai_os.knowledge.models import ChunkRecord, EmbeddingRecord, ProcessingState, utc_now


@dataclass
class ChunkDiff:
    added: list[ChunkRecord] = field(default_factory=list)
    changed: list[ChunkRecord] = field(default_factory=list)
    removed_ids: list[str] = field(default_factory=list)
    unchanged: list[ChunkRecord] = field(default_factory=list)


def diff_chunks(
    old_chunks: list[ChunkRecord],
    new_chunks: list[ChunkRecord],
) -> ChunkDiff:
    """Compare child chunks by content_hash to determine what needs re-embedding."""
    old_children = {c.chunk_id: c for c in old_chunks if c.chunk_level.value == "child"}
    new_children = {c.chunk_id: c for c in new_chunks if c.chunk_level.value == "child"}

    result = ChunkDiff()
    for chunk_id, chunk in new_children.items():
        prior = old_children.get(chunk_id)
        if prior is None:
            result.added.append(chunk)
        elif prior.content_hash == chunk.content_hash:
            result.unchanged.append(chunk)
        else:
            result.changed.append(chunk)

    for chunk_id in old_children:
        if chunk_id not in new_children:
            result.removed_ids.append(chunk_id)

    return result


def body_fingerprint(body: str) -> str:
    return content_hash(body)


def needs_reprocess(
    state: ProcessingState | None,
    *,
    source_fingerprint: str,
    pipeline_version: str,
) -> bool:
    if state is None:
        return True
    if state.source_fingerprint != source_fingerprint:
        return True
    if state.pipeline_version != pipeline_version:
        return True
    return False


def build_processing_state(
    *,
    doc_id: str,
    source_id: str,
    source_fingerprint: str,
    pipeline_version: str,
    chunks: list[ChunkRecord],
) -> ProcessingState:
    children = [c for c in chunks if c.chunk_level.value == "child"]
    return ProcessingState(
        doc_id=doc_id,
        source_id=source_id,
        source_fingerprint=source_fingerprint,
        pipeline_version=pipeline_version,
        chunk_count=len(chunks),
        child_chunk_count=len(children),
        last_processed_at=utc_now(),
    )


def merge_embeddings(
  diff: ChunkDiff,
  existing: dict[str, EmbeddingRecord],
  fresh: list[EmbeddingRecord],
) -> list[EmbeddingRecord]:
    """Combine cached embeddings for unchanged chunks with freshly embedded ones."""
    fresh_by_id = {e.chunk_id: e for e in fresh}
    merged: list[EmbeddingRecord] = []

    for chunk in diff.unchanged:
        embedding = existing.get(chunk.chunk_id)
        if embedding:
            merged.append(embedding.model_copy(update={"cache_hit": True}))

    for chunk in diff.added + diff.changed:
        embedding = fresh_by_id.get(chunk.chunk_id)
        if embedding:
            merged.append(embedding)

    return merged
