"""Provider adapter base."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

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
            if config.settings.get("disabled"):
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.DISABLED,
                    message="Disabled",
                )
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.NOT_CONFIGURED,
                message="Not configured",
            )
        if not config.credentials_present and self._requires_credentials():
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.MISSING_CREDENTIALS,
                message="Missing credentials",
            )
        try:
            ok = self.authenticate()
            latency = int((time.perf_counter() - start) * 1000)
            if ok:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.HEALTHY,
                    message="Healthy",
                    capabilities=self.discover_capabilities(),
                    latency_ms=latency,
                )
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.AUTHENTICATION_FAILED,
                message="Authentication failed",
                capabilities=self.discover_capabilities(),
                latency_ms=latency,
            )
        except httpx.ConnectError as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.NETWORK_ERROR,
                message=f"Network error: {exc}",
            )
        except httpx.TimeoutException as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.NETWORK_ERROR,
                message=f"Network timeout: {exc}",
            )
        except Exception as exc:
            msg = str(exc)
            if "401" in msg or "403" in msg or "unauthorized" in msg.lower():
                status = ProviderStatus.AUTHENTICATION_FAILED
            elif "connect" in msg.lower() or "timeout" in msg.lower():
                status = ProviderStatus.NETWORK_ERROR
            else:
                status = ProviderStatus.NETWORK_ERROR
            return ProviderHealth(
                provider_id=self.provider_id,
                status=status,
                message=msg,
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
