"""Memory retrieval — experience context for Agent Runtime."""

from __future__ import annotations

from datetime import timedelta

from ai_os.memory.config import MemorySettings
from ai_os.memory.models import (
    EpisodicMemory,
    MemoryBundle,
    MemorySearchQuery,
    MemoryStatus,
    MemoryType,
    ProceduralMemory,
    SemanticMemory,
    WorkingMemory,
    utc_now,
)
from ai_os.memory.store import MemoryStore


class MemoryRetrieval:
    """Retrieves relevant memories for orchestration — never queries Knowledge."""

    def __init__(self, settings: MemorySettings | None = None) -> None:
        self.settings = settings or MemorySettings()
        self.store = MemoryStore(self.settings)

    def search(self, query: MemorySearchQuery) -> list:
        types = query.memory_types or list(MemoryType)
        results = []
        for memory_type in types:
            for record in self.store.list_by_type(memory_type, status=MemoryStatus.ACTIVE):
                if not self._matches(record, query):
                    continue
                results.append(record)
        results.sort(key=lambda r: r.updated_at, reverse=True)
        return results[: query.limit]

    def retrieve_for_task(
        self,
        *,
        task_id: str,
        agent_id: str | None = None,
        workflow_id: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryBundle:
        """Load memories relevant to an executing task."""
        query = MemorySearchQuery(
            task_id=task_id,
            agent_id=agent_id,
            workflow_id=workflow_id,
            tags=tags or [],
            limit=self.settings.max_retrieval_items,
        )

        working = [
            r
            for r in self.search(
                MemorySearchQuery(
                    memory_types=[MemoryType.WORKING],
                    task_id=task_id,
                    limit=self.settings.max_retrieval_items,
                )
            )
            if isinstance(r, WorkingMemory)
        ]
        episodic = [
            r
            for r in self.search(
                MemorySearchQuery(
                    memory_types=[MemoryType.EPISODIC],
                    agent_id=agent_id,
                    workflow_id=workflow_id,
                    tags=tags or [],
                    limit=self.settings.max_retrieval_items,
                )
            )
            if isinstance(r, EpisodicMemory)
        ]
        semantic = [
            r
            for r in self.search(
                MemorySearchQuery(
                    memory_types=[MemoryType.SEMANTIC],
                    tags=tags or [],
                    limit=self.settings.max_retrieval_items,
                )
            )
            if isinstance(r, SemanticMemory)
        ]
        procedural = [
            r
            for r in self.search(
                MemorySearchQuery(
                    memory_types=[MemoryType.PROCEDURAL],
                    workflow_id=workflow_id,
                    limit=self.settings.max_retrieval_items,
                )
            )
            if isinstance(r, ProceduralMemory)
        ]

        _ = query  # reserved for future ranking
        summary = self._build_summary(working, episodic, semantic, procedural)
        return MemoryBundle(
            working=working,
            episodic=episodic,
            semantic=semantic,
            procedural=procedural,
            summary=summary,
        )

    def _matches(self, record, query: MemorySearchQuery) -> bool:
        if query.task_id and isinstance(record, WorkingMemory):
            if record.task_id != query.task_id:
                return False

        if query.agent_id:
            agent = record.metadata.get("agent_id")
            if agent and agent != query.agent_id:
                return False

        if query.workflow_id:
            workflow = record.metadata.get("workflow_id")
            if workflow and workflow != query.workflow_id:
                return False

        if query.tags and not set(query.tags).issubset(set(record.tags)):
            return False

        if query.since:
            occurred = getattr(record, "occurred_at", record.created_at)
            if occurred < query.since:
                return False

        if query.until:
            occurred = getattr(record, "occurred_at", record.created_at)
            if occurred > query.until:
                return False

        if query.query:
            haystack = self._record_text(record).lower()
            if query.query.lower() not in haystack:
                return False

        return True

    def _record_text(self, record) -> str:
        parts = [record.memory_id, record.memory_type.value]
        for attr in ("title", "summary", "concept", "abstraction", "procedure_name", "description"):
            value = getattr(record, attr, None)
            if value:
                parts.append(str(value))
        return " ".join(parts)

    def _build_summary(
        self,
        working: list[WorkingMemory],
        episodic: list[EpisodicMemory],
        semantic: list[SemanticMemory],
        procedural: list[ProceduralMemory],
    ) -> str:
        lines: list[str] = []
        for mem in semantic[:3]:
            lines.append(f"Lesson: {mem.concept} — {mem.abstraction}")
        for mem in episodic[:3]:
            lines.append(f"Past event ({mem.event_type.value}): {mem.title}")
        for mem in procedural[:2]:
            lines.append(f"Procedure: {mem.procedure_name} v{mem.version}")
        if working:
            lines.append(f"Active working context: {len(working)} item(s)")
        return "\n".join(lines)
