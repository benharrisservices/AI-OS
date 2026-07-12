"""Knowledge population tests."""

from pathlib import Path

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.populate import KnowledgeImporter


class TestKnowledgeImporter:
    def test_import_markdown_folder(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.md").write_text("# Hello\n\nWorld", encoding="utf-8")
        (docs / "b.txt").write_text("Plain text note", encoding="utf-8")

        settings = KnowledgeSettings(
            knowledge_raw_dir=tmp_path / "raw",
            knowledge_processed_dir=tmp_path / "processed",
            knowledge_index_dir=tmp_path / "index",
        )
        importer = KnowledgeImporter(settings)
        progress = importer.import_path(docs, source_type="folder", tags=["test"])
        assert progress.total == 2
        assert progress.ingested + progress.skipped == 2

    def test_duplicate_detection(self, tmp_path: Path) -> None:
        doc = tmp_path / "note.md"
        doc.write_text("# Same content", encoding="utf-8")
        settings = KnowledgeSettings(
            knowledge_raw_dir=tmp_path / "raw",
            knowledge_processed_dir=tmp_path / "processed",
            knowledge_index_dir=tmp_path / "index",
        )
        importer = KnowledgeImporter(settings)
        first = importer.import_path(doc, source_type="text")
        second = importer.import_path(doc, source_type="text")
        assert first.ingested == 1
        assert second.skipped == 1

    def test_import_chats_json(self, tmp_path: Path) -> None:
        import uuid

        unique = uuid.uuid4().hex[:8]
        chat = tmp_path / f"export-{unique}.json"
        chat.write_text(
            f'[{{"role": "user", "content": "Hello {unique}"}}, {{"role": "assistant", "content": "Hi"}}]',
            encoding="utf-8",
        )
        settings = KnowledgeSettings(
            knowledge_raw_dir=tmp_path / "raw",
            knowledge_processed_dir=tmp_path / "processed",
            knowledge_index_dir=tmp_path / "index",
        )
        importer = KnowledgeImporter(settings)
        progress = importer.import_path(chat, source_type="chats")
        assert progress.ingested == 1
