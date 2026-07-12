"""Capability Layer contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelRequirement(str, Enum):
    ANY = "any"
    REASONING = "reasoning"
    CODING = "coding"
    FAST = "fast"
    LOCAL = "local"
    CLOUD = "cloud"


class SkillMetadata(BaseModel):
    """Discoverable skill metadata exposed to Agent Runtime."""

    skill_id: str = Field(description="Stable skill identifier.")
    name: str = Field(description="Human-readable skill name.")
    description: str = Field(description="What this skill accomplishes.")
    version: str = Field(default="1.0.0")
    required_tools: list[str] = Field(default_factory=list)
    required_models: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class SkillInput(BaseModel):
    """Validated skill input."""

    data: dict[str, Any] = Field(default_factory=dict)


class SkillOutput(BaseModel):
    """Skill execution result with confidence scoring."""

    skill_id: str
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
