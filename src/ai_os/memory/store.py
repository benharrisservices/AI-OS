"""Memory persistence — separate from Knowledge Engine storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from ai_os.memory.config import MemorySettings
from ai_os.memory.models import (
    EpisodicMemory,
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    ProceduralMemory,
    SemanticMemory,
    WorkingMemory,
    utc_now,
)

T = TypeVar("T", WorkingMemory, EpisodicMemory, SemanticMemory, ProceduralMemory)

_TYPE_MODEL: dict[MemoryType, type] = {
    MemoryType.WORKING: WorkingMemory,
    MemoryType.EPISODIC: EpisodicMemory,
    MemoryType.SEMANTIC: SemanticMemory,
    MemoryType.PROCEDURAL: ProceduralMemory,
}

_TYPE_DIR_ATTR: dict[MemoryType, str] = {
    MemoryType.WORKING: "working_dir",
    MemoryType.EPISODIC: "episodic_dir",
    MemoryType.SEMANTIC: "semantic_dir",
    MemoryType.PROCEDURAL: "procedural_dir",
}


class MemoryStore:
    def __init__(self, settings: MemorySettings) -> None:
        self.settings = settings
        self.settings.ensure_dirs()

    def _dir_for(self, memory_type: MemoryType) -> Path:
        return getattr(self.settings, _TYPE_DIR_ATTR[memory_type])

    def _path_for(self, memory: MemoryRecord) -> Path:
        return self._dir_for(memory.memory_type) / f"{memory.memory_id}.json"

    def save(self, memory: MemoryRecord) -> None:
        memory.updated_at = utc_now()
        path = self._path_for(memory)
        path.write_text(
            json.dumps(memory.model_dump(mode="json"), indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        self._append_index(memory)

    def get(self, memory_id: str) -> MemoryRecord | None:
        for memory_type in MemoryType:
            path = self._dir_for(memory_type) / f"{memory_id}.json"
            if path.exists():
                return self._load(path, memory_type)
        return None

    def delete(self, memory_id: str) -> bool:
        record = self.get(memory_id)
        if record is None:
            return False
        path = self._path_for(record)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_by_type(
        self,
        memory_type: MemoryType,
        *,
        status: MemoryStatus | None = MemoryStatus.ACTIVE,
    ) -> list[MemoryRecord]:
        model = _TYPE_MODEL[memory_type]
        records: list[MemoryRecord] = []
        for path in sorted(self._dir_for(memory_type).glob("*.json")):
            if path.name == "index.jsonl":
                continue
            try:
                record = self._load(path, memory_type)
                if status is None or record.status == status:
                    records.append(record)
            except Exception:
                continue
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def list_all(self, *, status: MemoryStatus | None = None) -> list[MemoryRecord]:
        records: list[MemoryRecord] = []
        for memory_type in MemoryType:
            records.extend(self.list_by_type(memory_type, status=status))
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def _load(self, path: Path, memory_type: MemoryType) -> MemoryRecord:
        model = _TYPE_MODEL[memory_type]
        return model.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _append_index(self, memory: MemoryRecord) -> None:
        index_path = self._dir_for(memory.memory_type) / "index.jsonl"
        line = json.dumps(
            {
                "memory_id": memory.memory_id,
                "memory_type": memory.memory_type.value,
                "status": memory.status.value,
                "created_at": memory.created_at.isoformat(),
                "updated_at": memory.updated_at.isoformat(),
            },
            default=str,
        )
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
