"""Memory intelligence tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_os.memory.config import MemorySettings
from ai_os.memory.intelligence import MemoryIntelligence
from ai_os.memory.manager import MemoryManager
from ai_os.memory.models import EpisodicEventType, EpisodicMemory, SemanticMemory


@pytest.fixture
def memory_settings(tmp_path: Path) -> MemorySettings:
    base = tmp_path / "memory"
    return MemorySettings(
        MEMORY_WORKING_DIR=base / "working",
        MEMORY_EPISODIC_DIR=base / "episodic",
        MEMORY_SEMANTIC_DIR=base / "semantic",
        MEMORY_PROCEDURAL_DIR=base / "procedural",
    )


@pytest.fixture
def intel(memory_settings: MemorySettings) -> MemoryIntelligence:
    return MemoryIntelligence(memory_settings)


@pytest.fixture
def manager(memory_settings: MemorySettings) -> MemoryManager:
    return MemoryManager(memory_settings)


class TestMemoryIntelligence:
    def test_timeline(self, intel: MemoryIntelligence, manager: MemoryManager) -> None:
        manager.create_episodic(
            event_type=EpisodicEventType.SUCCESS,
            title="Completed review",
            summary="Daily review done",
        )
        timeline = intel.build_timeline(limit=10)
        assert len(timeline) == 1
        assert timeline[0]["title"] == "Completed review"

    def test_importance_scoring(self, intel: MemoryIntelligence, manager: MemoryManager) -> None:
        em = manager.create_episodic(
            event_type=EpisodicEventType.DECISION,
            title="Important",
            summary="Key decision",
        )
        sm = manager.create_semantic(
            concept="Preference",
            abstraction="Morning reviews work best",
            promoted_from=em.memory_id,
            promotion_approved=True,
            confidence=0.9,
        )
        assert intel.score_importance(sm.memory_id) > intel.score_importance(em.memory_id)

    def test_duplicate_detection(self, intel: MemoryIntelligence, manager: MemoryManager) -> None:
        for _ in range(2):
            manager.create_episodic(
                event_type=EpisodicEventType.CUSTOM,
                title="Same event",
                summary="Identical summary text here",
            )
        dupes = intel.detect_duplicates()
        assert len(dupes) >= 1

    def test_semantic_clustering(self, intel: MemoryIntelligence, manager: MemoryManager) -> None:
        manager.create_semantic(
            concept="Morning habits",
            abstraction="Review before noon",
            promoted_from="emem_x",
            promotion_approved=True,
        )
        manager.create_semantic(
            concept="Morning routine",
            abstraction="Start with email",
            promoted_from="emem_y",
            promotion_approved=True,
        )
        clusters = intel.cluster_semantic()
        assert "morning" in clusters

    def test_contradiction_detection(self, intel: MemoryIntelligence, manager: MemoryManager) -> None:
        manager.create_semantic(
            concept="Budget",
            abstraction="Increase spending",
            promoted_from="a",
            promotion_approved=True,
        )
        manager.create_semantic(
            concept="budget",
            abstraction="Reduce spending",
            promoted_from="b",
            promotion_approved=True,
        )
        contradictions = intel.detect_contradictions()
        assert len(contradictions) == 1

    def test_promotion_recommendations(self, intel: MemoryIntelligence, manager: MemoryManager) -> None:
        manager.create_episodic(
            event_type=EpisodicEventType.SUCCESS,
            title="Major milestone",
            summary="Completed phase 4 automation layer",
            tags=["milestone"],
        )
        recs = intel.promotion_recommendations()
        assert isinstance(recs, list)

    def test_compress_episodic(self, intel: MemoryIntelligence, manager: MemoryManager) -> None:
        manager.create_episodic(
            event_type=EpisodicEventType.WORKFLOW_EXECUTION,
            title="Run 1",
            summary="Workflow completed",
        )
        digest = intel.compress_episodic()
        assert digest["count"] >= 1

    def test_relationship_graph(self, intel: MemoryIntelligence, manager: MemoryManager) -> None:
        em = manager.create_episodic(
            event_type=EpisodicEventType.SUCCESS,
            title="E",
            summary="S",
            source_ref="task_abc",
        )
        manager.create_semantic(
            concept="Lesson",
            abstraction="Learned",
            promoted_from=em.memory_id,
            promotion_approved=True,
        )
        graph = intel.build_relationship_graph()
        assert em.memory_id in graph

    def test_uses_manager_public_api_only(self) -> None:
        from pathlib import Path
        source = Path(__import__("ai_os.memory.intelligence", fromlist=["*"]).__file__).read_text()
        assert "MemoryStore" not in source
        assert "MemoryRetrieval" not in source
