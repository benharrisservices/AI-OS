from pathlib import Path

import pytest

from ai_os.knowledge.chunking import chunk_document
from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.extractors.bootstrap import register_builtin_extractors
from ai_os.knowledge.extractors import extract_document
from ai_os.knowledge.ids import chunk_id, content_hash, fingerprint_bytes
from ai_os.knowledge.models import DocumentRecord, Format
from ai_os.knowledge.normalize import normalize_body
from ai_os.knowledge.search import reciprocal_rank_fusion
from ai_os.knowledge.models import SearchHit


@pytest.fixture
def settings(tmp_path: Path) -> KnowledgeSettings:
    return KnowledgeSettings(
        KNOWLEDGE_RAW_DIR=tmp_path / "raw",
        KNOWLEDGE_PROCESSED_DIR=tmp_path / "processed",
        KNOWLEDGE_INDEX_DIR=tmp_path / "index",
        VECTOR_STORE_PATH=tmp_path / "index" / "vectors",
    )


def test_fingerprint_is_deterministic() -> None:
    data = b"hello world"
    assert fingerprint_bytes(data) == fingerprint_bytes(data)


def test_chunk_id_is_deterministic() -> None:
    first = chunk_id("doc_abc", "intro", "hello", 0, "child")
    second = chunk_id("doc_abc", "intro", "hello", 0, "child")
    assert first == second


def test_content_hash_prefix() -> None:
    assert content_hash("test").startswith("sha256:")


def test_normalize_body_unifies_newlines() -> None:
    assert normalize_body("a\r\nb\r\nc") == "a\nb\nc"


def test_markdown_extractor() -> None:
    register_builtin_extractors()
    data = Path("tests/fixtures/barbados-solar.md").read_bytes()
    doc = extract_document(data, Format.MARKDOWN, Path("barbados-solar.md"))
    assert "Barbados solar" in doc.body
    assert doc.title == "Barbados Solar Project"


def test_chunk_document_creates_parents_and_children(settings: KnowledgeSettings) -> None:
    register_builtin_extractors()
    data = Path("tests/fixtures/barbados-solar.md").read_bytes()
    extracted = extract_document(data, Format.MARKDOWN, Path("barbados-solar.md"))
    document = DocumentRecord(
        doc_id="doc_test",
        source_id="src_test",
        title=extracted.title,
        format=Format.MARKDOWN,
        source_uri="file:///tmp/barbados-solar.md",
        raw_path="knowledge/raw/src_test/original.md",
        processed_path="knowledge/processed/documents/doc_test/document.md",
    )
    chunks = chunk_document(document, extracted.body, settings)
    assert chunks
    parents = [c for c in chunks if c.chunk_level.value == "parent"]
    children = [c for c in chunks if c.chunk_level.value == "child"]
    assert parents
    assert children
    assert all(c.parent_chunk_id for c in children)


def test_reciprocal_rank_fusion() -> None:
    a = SearchHit(
        chunk_id="a",
        doc_id="d1",
        source_id="s1",
        score=0.9,
        title="A",
        heading_path="",
        excerpt="",
        source_uri="",
    )
    b = SearchHit(
        chunk_id="b",
        doc_id="d1",
        source_id="s1",
        score=0.8,
        title="B",
        heading_path="",
        excerpt="",
        source_uri="",
    )
    fused = reciprocal_rank_fusion([[a], [b, a]])
    assert fused[0].chunk_id in {"a", "b"}
