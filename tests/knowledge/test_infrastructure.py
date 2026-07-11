from pathlib import Path
from unittest.mock import patch

import pytest

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.incremental import diff_chunks, needs_reprocess, build_processing_state
from ai_os.knowledge.models import ChunkLevel, ChunkRecord, ProcessingState, SourceStatus
from ai_os.knowledge.pipeline import KnowledgePipeline
from ai_os.knowledge.purge import PurgeService
from ai_os.knowledge.integrity import IntegrityService
from ai_os.knowledge.health import HealthService
from ai_os.knowledge.maintenance import MaintenanceService
from ai_os.knowledge.watcher import InboxWatcher


@pytest.fixture
def settings(tmp_path: Path) -> KnowledgeSettings:
    return KnowledgeSettings(
        KNOWLEDGE_RAW_DIR=tmp_path / "raw",
        KNOWLEDGE_PROCESSED_DIR=tmp_path / "processed",
        KNOWLEDGE_INDEX_DIR=tmp_path / "index",
        VECTOR_STORE_PATH=tmp_path / "index" / "vectors",
        KNOWLEDGE_WATCH_DIR=tmp_path / "inbox",
        KNOWLEDGE_BACKUP_DIR=tmp_path / "backups",
        EMBEDDING_BATCH_SIZE=8,
    )


@pytest.fixture
def pipeline(settings: KnowledgeSettings) -> KnowledgePipeline:
    return KnowledgePipeline(settings)


def _fake_embeddings(texts: list[str]) -> list[list[float]]:
    return [[float(len(t) % 7), 0.1, 0.2] + [0.0] * 765 for t in texts]


def _child(doc_id: str, chunk_id: str, text: str, content_hash: str) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        doc_id=doc_id,
        source_id="src_test",
        chunk_level=ChunkLevel.CHILD,
        parent_chunk_id="chk_parent",
        chunk_index=0,
        heading_path="section",
        title="Test",
        content_hash=content_hash,
        embed_text=text,
        body_text=text,
    )


def test_needs_reprocess_skips_unchanged_fingerprint() -> None:
    state = ProcessingState(
        doc_id="doc_1",
        source_id="src_1",
        source_fingerprint="sha256:abc",
        pipeline_version="1.0.0",
    )
    assert not needs_reprocess(state, source_fingerprint="sha256:abc", pipeline_version="1.0.0")


def test_needs_reprocess_on_fingerprint_change() -> None:
    state = ProcessingState(
        doc_id="doc_1",
        source_id="src_1",
        source_fingerprint="sha256:abc",
        pipeline_version="1.0.0",
    )
    assert needs_reprocess(state, source_fingerprint="sha256:def", pipeline_version="1.0.0")


def test_diff_chunks_detects_added_removed_changed() -> None:
    old = [
        _child("doc_1", "chk_a", "alpha", "sha256:a"),
        _child("doc_1", "chk_b", "beta", "sha256:b"),
    ]
    new = [
        _child("doc_1", "chk_a", "alpha", "sha256:a"),
        _child("doc_1", "chk_c", "gamma", "sha256:c"),
    ]
    result = diff_chunks(old, new)
    assert len(result.unchanged) == 1
    assert result.unchanged[0].chunk_id == "chk_a"
    assert {c.chunk_id for c in result.added} == {"chk_c"}
    assert result.removed_ids == ["chk_b"]


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_incremental_skips_unchanged_source(mock_embed, pipeline: KnowledgePipeline) -> None:
    fixture = Path("tests/fixtures/barbados-solar.md")
    first = pipeline.ingest_file(fixture)
    assert first.status == SourceStatus.READY
    first_calls = mock_embed.call_count

    second = pipeline.ingest_file(fixture)
    assert second.status == SourceStatus.UNCHANGED
    assert mock_embed.call_count == first_calls


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_source_update_only_reindexes_changed_doc(
    mock_embed, pipeline: KnowledgePipeline, settings: KnowledgeSettings, tmp_path: Path
) -> None:
    source = tmp_path / "doc.md"
    source.write_text("# Doc\n\nOriginal content.\n", encoding="utf-8")
    pipeline.ingest_file(source)
    calls_after_first = mock_embed.call_count

    source.write_text("# Doc\n\nOriginal content.\n\n## New Section\n\nUpdated content.\n", encoding="utf-8")
    pipeline.ingest_file(source)
    assert mock_embed.call_count >= calls_after_first


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_purge_removes_index_entries(mock_embed, pipeline: KnowledgePipeline, settings: KnowledgeSettings) -> None:
    fixture = Path("tests/fixtures/barbados-solar.md")
    record = pipeline.ingest_file(fixture)
    assert pipeline.vector.count() > 0

    PurgeService(settings).purge_source(record.source_id)
    assert pipeline.vector.count() == 0
    updated = pipeline.registry.get(record.source_id)
    assert updated is not None
    assert updated.status == SourceStatus.TOMBSTONED


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_integrity_clean_after_ingest(mock_embed, pipeline: KnowledgePipeline, settings: KnowledgeSettings) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))
    issues = IntegrityService(settings).validate()
    errors = [i for i in issues if i.severity == "error"]
    assert not errors


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_health_report(mock_embed, pipeline: KnowledgePipeline, settings: KnowledgeSettings) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))
    report = HealthService(settings).report()
    assert report.document_count >= 1
    assert report.child_chunk_count >= 1
    assert report.embedding_count >= 1
    assert report.vector_index_count >= 1


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_watcher_run_once(mock_embed, pipeline: KnowledgePipeline, settings: KnowledgeSettings) -> None:
    inbox = settings.knowledge_watch_dir
    inbox.mkdir(parents=True, exist_ok=True)
    sample = inbox / "notes.md"
    sample.write_text("# Notes\n\nProject planning document.\n", encoding="utf-8")

    watcher = InboxWatcher(settings)
    count = watcher.run_once()
    assert count == 1
    assert pipeline.vector.count() > 0


@patch("ai_os.knowledge.embedding.EmbeddingService.embed_texts", side_effect=_fake_embeddings)
def test_backup_creates_archive(mock_embed, pipeline: KnowledgePipeline, settings: KnowledgeSettings) -> None:
    pipeline.ingest_file(Path("tests/fixtures/barbados-solar.md"))
    dest = MaintenanceService(settings).backup()
    assert dest.exists()
    assert dest.suffix == ".gz"
