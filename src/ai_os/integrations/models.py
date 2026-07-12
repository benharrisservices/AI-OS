"""Integration contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


class ProviderCapability(BaseModel):
    name: str
    description: str = ""


class ProviderHealth(BaseModel):
    provider_id: str
    status: ProviderStatus
    message: str = ""
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    latency_ms: int = 0


class ProviderConfig(BaseModel):
    provider_id: str
    enabled: bool = False
    credentials_present: bool = False
    settings: dict[str, Any] = Field(default_factory=dict)
