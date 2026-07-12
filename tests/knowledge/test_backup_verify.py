"""Maintenance backup verification tests."""

from pathlib import Path

import tarfile

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.maintenance import MaintenanceService


class TestBackupVerification:
    def test_verify_backup_missing(self, tmp_path: Path) -> None:
        settings = KnowledgeSettings(knowledge_backup_dir=tmp_path / "backups")
        ok, msg = MaintenanceService(settings).verify_backup()
        assert ok is False
        assert "No backups found" in msg

    def test_verify_backup_valid(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        backup_path = backup_dir / "knowledge-backup-test.tar.gz"
        with tarfile.open(backup_path, "w:gz") as archive:
            archive.addfile(tarfile.TarInfo("knowledge/raw/.keep"))
            archive.addfile(tarfile.TarInfo("knowledge/processed/.keep"))
            archive.addfile(tarfile.TarInfo("knowledge/index/.keep"))

        settings = KnowledgeSettings(knowledge_backup_dir=backup_dir)
        ok, msg = MaintenanceService(settings).verify_backup(backup_path)
        assert ok is True
        assert "verified" in msg
