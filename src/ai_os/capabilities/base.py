"""Base skill implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ai_os.capabilities.models import SkillMetadata, SkillOutput


class BaseSkill(ABC):
    """Reusable capability — composes existing engines, never duplicates orchestration."""

    metadata: SkillMetadata

    @abstractmethod
    def execute(self, input_data: dict[str, Any]) -> SkillOutput:
        """Run the skill and return structured output with confidence."""

    def _success(
        self,
        *,
        result: dict[str, Any],
        summary: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> SkillOutput:
        return SkillOutput(
            skill_id=self.metadata.skill_id,
            success=True,
            result=result,
            summary=summary,
            confidence=min(1.0, max(0.0, confidence)),
            metadata=metadata or {},
        )

    def _failure(self, error: str, confidence: float = 0.0) -> SkillOutput:
        return SkillOutput(
            skill_id=self.metadata.skill_id,
            success=False,
            error=error,
            confidence=confidence,
        )

    @staticmethod
    def confidence_from_evidence(chunk_count: int, citation_count: int) -> float:
        if chunk_count == 0:
            return 0.2
        base = min(0.5 + chunk_count * 0.05, 0.85)
        if citation_count > 0:
            base = min(base + 0.1, 0.95)
        return base
