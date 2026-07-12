"""Integration contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    AUTHENTICATION_FAILED = "authentication_failed"
    MISSING_CREDENTIALS = "missing_credentials"
    NETWORK_ERROR = "network_error"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    # Legacy aliases kept for backward compatibility in API consumers.
    DEGRADED = "authentication_failed"
    UNAVAILABLE = "network_error"


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
