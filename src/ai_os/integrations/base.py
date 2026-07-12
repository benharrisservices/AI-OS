"""Provider adapter base."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from ai_os.integrations.config import IntegrationSettings
from ai_os.integrations.models import ProviderCapability, ProviderConfig, ProviderHealth, ProviderStatus


class ProviderAdapter(ABC):
    """Optional external service adapter with health check and graceful failure."""

    provider_id: str
    name: str

    def __init__(self, settings: IntegrationSettings | None = None) -> None:
        self.settings = settings or IntegrationSettings()

    @abstractmethod
    def configure(self) -> ProviderConfig: ...

    @abstractmethod
    def authenticate(self) -> bool: ...

    @abstractmethod
    def discover_capabilities(self) -> list[ProviderCapability]: ...

    def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        config = self.configure()
        if not config.enabled:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.NOT_CONFIGURED,
                message="Provider not configured",
            )
        if not config.credentials_present and self._requires_credentials():
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.NOT_CONFIGURED,
                message="Credentials missing",
            )
        try:
            ok = self.authenticate()
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.HEALTHY if ok else ProviderStatus.DEGRADED,
                message="OK" if ok else "Authentication failed",
                capabilities=self.discover_capabilities(),
                latency_ms=latency,
            )
        except Exception as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                message=str(exc),
            )

    def invoke(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        """Invoke a capability with retry policy."""
        last_error: str | None = None
        for attempt in range(self.settings.retry_attempts):
            try:
                return self._invoke(capability, params)
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.settings.retry_attempts - 1:
                    time.sleep(self.settings.retry_backoff_seconds * (attempt + 1))
        return {"success": False, "error": last_error or "Unknown error"}

    @abstractmethod
    def _invoke(self, capability: str, params: dict[str, Any]) -> dict[str, Any]: ...

    def _requires_credentials(self) -> bool:
        return True
