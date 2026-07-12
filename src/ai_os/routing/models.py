"""Model routing contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RoutingPriority(str, Enum):
    LATENCY = "latency"
    COST = "cost"
    QUALITY = "quality"
    CODING = "coding"
    REASONING = "reasoning"
    LOCAL = "local"


class ModelProfile(BaseModel):
    provider_id: str
    model_id: str
    context_length: int = 8192
    supports_structured_output: bool = False
    supports_multimodal: bool = False
    reasoning_score: float = Field(default=0.5, ge=0.0, le=1.0)
    coding_score: float = Field(default=0.5, ge=0.0, le=1.0)
    latency_score: float = Field(default=0.5, ge=0.0, le=1.0)
    cost_score: float = Field(default=0.5, ge=0.0, le=1.0)
    is_local: bool = False


class ModelRequest(BaseModel):
    task: str = ""
    priorities: list[RoutingPriority] = Field(default_factory=list)
    min_context_length: int = 0
    require_structured_output: bool = False
    require_multimodal: bool = False
    override_provider: str | None = None
    override_model: str | None = None


class ModelRoute(BaseModel):
    provider_id: str
    model_id: str
    score: float
    fallback_chain: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
