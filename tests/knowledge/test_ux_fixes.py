"""Post-import index and backup verification tests."""

from pathlib import Path

import tarfile

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.maintenance import MaintenanceService


class TestEnsureSearchIndexes:
    def test_ensure_search_indexes_noop_when_aligned(self, tmp_path: Path) -> None:
        settings = KnowledgeSettings(
            knowledge_raw_dir=tmp_path / "raw",
            knowledge_processed_dir=tmp_path / "processed",
            knowledge_index_dir=tmp_path / "index",
            knowledge_backup_dir=tmp_path / "backups",
        )
        settings.ensure_dirs()
        service = MaintenanceService(settings)
        assert service.ensure_search_indexes() is False


class TestBackupVerifyCLI:
    def test_verify_backup_after_create(self, tmp_path: Path) -> None:
        settings = KnowledgeSettings(
            knowledge_raw_dir=tmp_path / "raw",
            knowledge_processed_dir=tmp_path / "processed",
            knowledge_index_dir=tmp_path / "index",
            knowledge_backup_dir=tmp_path / "backups",
        )
        for sub in ("raw", "processed", "index"):
            (tmp_path / sub).mkdir(parents=True)
            (tmp_path / sub / ".keep").write_text("x")
        service = MaintenanceService(settings)
        dest = service.backup()
        ok, msg = service.verify_backup(dest)
        assert ok is True
        assert "verified" in msg
