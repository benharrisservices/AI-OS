"""Memory System tests."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
import yaml

from ai_os.agent.config import AgentSettings
from ai_os.agent.engine import ExecutionEngine
from ai_os.agent.models import Agent, TaskStatus, ToolPermission, Workflow, WorkflowStep
from ai_os.agent.tools import discover_tools
from ai_os.memory.config import MemorySettings
from ai_os.memory.manager import MemoryManager
from ai_os.memory.models import (
    EpisodicEventType,
    EpisodicMemory,
    MemorySearchQuery,
    MemoryStatus,
    MemoryType,
    PromotionPolicy,
    PromotionRequest,
    PromotionTarget,
    SemanticMemory,
    WorkingMemory,
    utc_now,
)
from ai_os.memory.promotion import PromotionEngine
from ai_os.memory.store import MemoryStore


@pytest.fixture
def memory_settings(tmp_path: Path) -> MemorySettings:
    base = tmp_path / "memory"
    settings = MemorySettings(
        MEMORY_WORKING_DIR=base / "working",
        MEMORY_EPISODIC_DIR=base / "episodic",
        MEMORY_SEMANTIC_DIR=base / "semantic",
        MEMORY_PROCEDURAL_DIR=base / "procedural",
        MEMORY_WORKING_TTL_MINUTES=1,
    )
    settings.ensure_dirs()
    return settings


@pytest.fixture
def memory_manager(memory_settings: MemorySettings) -> MemoryManager:
    return MemoryManager(memory_settings)


class TestContracts:
    def test_memory_types_are_distinct(self) -> None:
        assert MemoryType.WORKING != MemoryType.EPISODIC
        assert len(MemoryType) == 4

    def test_working_memory_has_expiration(self, memory_manager: MemoryManager) -> None:
        record = memory_manager.create_working(scope="session", content={"key": "value"})
        assert record.memory_type == MemoryType.WORKING
        assert record.expires_at > record.created_at

    def test_semantic_requires_approval_flag(self, memory_manager: MemoryManager) -> None:
        with pytest.raises(ValueError, match="explicit promotion approval"):
            memory_manager.create_semantic(
                concept="test",
                abstraction="lesson",
                promoted_from="emem_fake",
                promotion_approved=False,
            )


class TestPersistence:
    def test_store_round_trip(self, memory_manager: MemoryManager) -> None:
        episodic = memory_manager.create_episodic(
            event_type=EpisodicEventType.DECISION,
            title="Chose strategy",
            summary="Selected analytical approach",
            source_ref="dec_test",
        )
        loaded = memory_manager.get(episodic.memory_id)
        assert loaded is not None
        assert isinstance(loaded, EpisodicMemory)
        assert loaded.title == "Chose strategy"

    def test_list_by_type_excludes_other_types(self, memory_manager: MemoryManager) -> None:
        memory_manager.create_working(scope="task")
        memory_manager.create_episodic(
            event_type=EpisodicEventType.SUCCESS,
            title="Done",
            summary="Completed",
        )
        episodic = memory_manager.store.list_by_type(MemoryType.EPISODIC)
        assert len(episodic) == 1
        assert episodic[0].memory_type == MemoryType.EPISODIC


class TestExpiration:
    def test_expire_working_past_ttl(self, memory_manager: MemoryManager) -> None:
        record = memory_manager.create_working(scope="temp", ttl_minutes=0)
        record.expires_at = utc_now() - timedelta(minutes=1)
        memory_manager.store.save(record)

        expired = memory_manager.expire_working()
        assert record.memory_id in expired

        loaded = memory_manager.get(record.memory_id)
        assert loaded is not None
        assert loaded.status == MemoryStatus.EXPIRED


class TestPromotion:
    def test_working_to_episodic(self, memory_manager: MemoryManager) -> None:
        working = memory_manager.create_working(
            scope="workflow:test",
            content={"step": "done"},
            metadata={"title": "Run complete", "summary": "Workflow finished"},
        )
        result = memory_manager.promote(
            PromotionRequest(
                source_memory_id=working.memory_id,
                target_type=PromotionTarget.EPISODIC,
                policy=PromotionPolicy.WORKFLOW_COMPLETION,
                approved=True,
            )
        )
        assert result.success
        assert result.target_memory_id is not None

        source = memory_manager.get(working.memory_id)
        target = memory_manager.get(result.target_memory_id)
        assert source is not None and source.status == MemoryStatus.PROMOTED
        assert target is not None and isinstance(target, EpisodicMemory)

    def test_episodic_to_semantic_requires_approval(self, memory_manager: MemoryManager) -> None:
        episodic = memory_manager.create_episodic(
            event_type=EpisodicEventType.SUCCESS,
            title="Pattern observed",
            summary="Morning reviews work best",
        )
        denied = memory_manager.promote(
            PromotionRequest(
                source_memory_id=episodic.memory_id,
                target_type=PromotionTarget.SEMANTIC,
                policy=PromotionPolicy.MANUAL_APPROVAL,
                approved=False,
            )
        )
        assert not denied.success
        assert "approval" in (denied.error or "").lower()

        approved = memory_manager.promote(
            PromotionRequest(
                source_memory_id=episodic.memory_id,
                target_type=PromotionTarget.SEMANTIC,
                policy=PromotionPolicy.MANUAL_APPROVAL,
                approved=True,
                concept="Review timing",
                abstraction="Morning reviews work best",
            )
        )
        assert approved.success
        semantic = memory_manager.get(approved.target_memory_id)
        assert isinstance(semantic, SemanticMemory)
        assert semantic.promotion_approved is True

    def test_working_cannot_skip_to_semantic(self, memory_manager: MemoryManager) -> None:
        working = memory_manager.create_working(scope="session")
        result = PromotionEngine(memory_manager.store).promote(
            PromotionRequest(
                source_memory_id=working.memory_id,
                target_type=PromotionTarget.SEMANTIC,
                policy=PromotionPolicy.MANUAL_APPROVAL,
                approved=True,
            )
        )
        assert not result.success
        assert "bypass" in (result.error or "").lower()


class TestRetrieval:
    def test_search_by_query_text(self, memory_manager: MemoryManager) -> None:
        memory_manager.create_episodic(
            event_type=EpisodicEventType.FAILURE,
            title="Deployment failed",
            summary="Rollback required after timeout",
        )
        results = memory_manager.search(MemorySearchQuery(query="rollback", limit=5))
        assert len(results) == 1

    def test_retrieve_for_task_scopes_working(self, memory_manager: MemoryManager) -> None:
        memory_manager.create_working(scope="workflow", task_id="task_abc", content={"x": 1})
        memory_manager.create_working(scope="other", task_id="task_xyz", content={"y": 2})

        bundle = memory_manager.retrieval.retrieve_for_task(task_id="task_abc")
        assert len(bundle.working) == 1
        assert bundle.working[0].task_id == "task_abc"

    def test_retrieval_separate_from_knowledge(self) -> None:
        """Memory retrieval module must not import Knowledge Engine."""
        import ai_os.memory.retrieval as retrieval_module

        source = Path(retrieval_module.__file__).read_text(encoding="utf-8")
        assert "ai_os.knowledge" not in source


class TestArchive:
    def test_archive_episodic(self, memory_manager: MemoryManager) -> None:
        record = memory_manager.create_episodic(
            event_type=EpisodicEventType.CONVERSATION,
            title="Chat",
            summary="Discussed roadmap",
        )
        archived = memory_manager.archive(record.memory_id)
        assert archived.status == MemoryStatus.ARCHIVED
        assert isinstance(archived, EpisodicMemory)
        assert archived.archived_at is not None


class TestProceduralMemory:
    def test_versioned_procedure(self, memory_manager: MemoryManager) -> None:
        v1 = memory_manager.create_procedural(
            procedure_name="daily-review",
            description="Morning review workflow",
            steps=[{"step_id": "retrieve", "tool_name": "knowledge_retrieve"}],
            version="1.0.0",
        )
        v2 = memory_manager.create_procedural(
            procedure_name="daily-review",
            description="Morning review with notify",
            steps=[
                {"step_id": "retrieve", "tool_name": "knowledge_retrieve"},
                {"step_id": "notify", "tool_name": "filesystem_write"},
            ],
            version="1.1.0",
            previous_version_id=v1.memory_id,
        )
        assert v2.previous_version_id == v1.memory_id
        assert v2.version == "1.1.0"


class TestAgentIntegration:
    def test_runtime_injects_memories(
        self, tmp_path: Path, memory_manager: MemoryManager
    ) -> None:
        memory_manager.create_semantic(
            concept="Review habit",
            abstraction="Run reviews before noon",
            promoted_from="emem_seed",
            promotion_approved=True,
        )

        agent_base = tmp_path / "agent"
        agent_settings = AgentSettings(
            AGENT_TASKS_DIR=agent_base / "tasks",
            AGENT_LOGS_DIR=agent_base / "logs",
            AGENT_WORKFLOWS_DIR=agent_base / "workflows",
            AGENT_DEFINITIONS_DIR=agent_base / "agents",
        )
        agent_settings.ensure_dirs()

        agent = Agent(
            agent_id="agt_tester",
            name="Tester",
            description="Test",
            tools=["datetime_now"],
            permissions=[ToolPermission.SYSTEM_READ],
        )
        (agent_settings.agents_dir / "tester.yaml").write_text(
            yaml.dump(agent.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
        )

        workflow = Workflow(
            workflow_id="mem-flow",
            name="Memory Flow",
            description="Test memory injection",
            agent_id="agt_tester",
            steps=[WorkflowStep(step_id="ts", name="Timestamp", tool_name="datetime_now", input={})],
        )
        (agent_settings.workflows_dir / "mem-flow.yaml").write_text(
            yaml.dump(workflow.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
        )

        discover_tools(agent_settings)
        engine = ExecutionEngine(agent_settings, memory_manager=memory_manager)
        result = engine.run_workflow("mem-flow", {})
        assert result.status == TaskStatus.COMPLETED

        task = engine.store.get_task(result.task_id)
        assert task is not None
        assert "summary" in task.context.relevant_memories
        assert "Review habit" in task.context.relevant_memories.get("summary", "")

    def test_workflow_creates_episodic_memory(
        self, tmp_path: Path, memory_manager: MemoryManager
    ) -> None:
        agent_base = tmp_path / "agent"
        agent_settings = AgentSettings(
            AGENT_TASKS_DIR=agent_base / "tasks",
            AGENT_LOGS_DIR=agent_base / "logs",
            AGENT_WORKFLOWS_DIR=agent_base / "workflows",
            AGENT_DEFINITIONS_DIR=agent_base / "agents",
        )
        agent_settings.ensure_dirs()

        agent = Agent(
            agent_id="agt_tester",
            name="Tester",
            description="Test",
            tools=["datetime_now"],
            permissions=[ToolPermission.SYSTEM_READ],
        )
        (agent_settings.agents_dir / "tester.yaml").write_text(
            yaml.dump(agent.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
        )
        workflow = Workflow(
            workflow_id="ep-flow",
            name="Episodic Flow",
            description="Record episodic memory",
            agent_id="agt_tester",
            steps=[WorkflowStep(step_id="ts", name="Timestamp", tool_name="datetime_now", input={})],
        )
        (agent_settings.workflows_dir / "ep-flow.yaml").write_text(
            yaml.dump(workflow.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
        )

        discover_tools(agent_settings)
        engine = ExecutionEngine(agent_settings, memory_manager=memory_manager)
        result = engine.run_workflow("ep-flow", {})
        assert result.status == TaskStatus.COMPLETED

        episodic = memory_manager.store.list_by_type(MemoryType.EPISODIC)
        assert any(e.source_ref == result.task_id for e in episodic)
