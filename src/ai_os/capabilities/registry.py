"""Skill registry — auto-discovery for Agent Runtime."""

from __future__ import annotations

from typing import Protocol

from ai_os.capabilities.base import BaseSkill
from ai_os.capabilities.models import SkillMetadata

_REGISTRY: dict[str, BaseSkill] = {}


class Skill(Protocol):
    metadata: SkillMetadata

    def execute(self, input_data: dict) -> object: ...


def register_skill(skill: BaseSkill) -> None:
    _REGISTRY[skill.metadata.skill_id] = skill


def get_skill(skill_id: str) -> BaseSkill | None:
    return _REGISTRY.get(skill_id)


def list_skills() -> list[BaseSkill]:
    return sorted(_REGISTRY.values(), key=lambda s: s.metadata.skill_id)


def discover_skills() -> list[str]:
    """Load and register all built-in skills."""
    from ai_os.capabilities.builtin import register_builtin_skills

    register_builtin_skills()
    return list(_REGISTRY.keys())


def register_skills_as_tools() -> list[str]:
    """Register skills as Agent Runtime tools."""
    from ai_os.capabilities.tools import register_skill_tools

    discover_skills()
    return register_skill_tools()
