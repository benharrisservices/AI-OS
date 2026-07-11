"""Source registry backed by JSONL."""

from __future__ import annotations

from pathlib import Path

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.io import append_jsonl, read_jsonl, write_json
from ai_os.knowledge.models import SourceRegistryRecord, SourceStatus, utc_now


class SourceRegistry:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.path = settings.knowledge_raw_dir / ".registry" / "sources.jsonl"

    def _load_all(self) -> list[SourceRegistryRecord]:
        records = [
            SourceRegistryRecord.model_validate(row)
            for row in read_jsonl(self.path)
        ]
        latest: dict[str, SourceRegistryRecord] = {}
        for record in records:
            latest[record.source_id] = record
        return list(latest.values())

    def find_by_uri(self, uri: str) -> SourceRegistryRecord | None:
        for record in self._load_all():
            if record.original_uri == uri and record.status != SourceStatus.TOMBSTONED:
                return record
        return None

    def get(self, source_id: str) -> SourceRegistryRecord | None:
        for record in self._load_all():
            if record.source_id == source_id:
                return record
        return None

    def upsert(self, record: SourceRegistryRecord) -> None:
        record.updated_at = utc_now()
        append_jsonl(self.path, record)

    def list_ready(self) -> list[SourceRegistryRecord]:
        return [r for r in self._load_all() if r.status == SourceStatus.READY]

    def write_snapshot(self, source_id: str, record: SourceRegistryRecord) -> None:
        dest = self.settings.knowledge_raw_dir / source_id / "registry.json"
        write_json(dest, record)
