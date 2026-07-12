"""HTTP-based provider helpers."""

from __future__ import annotations

import os
from typing import Any

import httpx

from ai_os.integrations.base import ProviderAdapter
from ai_os.integrations.models import ProviderCapability, ProviderConfig


class HttpProvider(ProviderAdapter):
    """Base for REST API providers with timeout and auth."""

    base_url: str = ""
    _env_keys: list[str] = []
    _capabilities: list[ProviderCapability] = []
    _auth_header: str = "Authorization"
    _auth_prefix: str = "Bearer"

    def configure(self) -> ProviderConfig:
        present = any(os.environ.get(k) for k in self._env_keys)
        return ProviderConfig(
            provider_id=self.provider_id,
            enabled=present or not self._requires_credentials(),
            credentials_present=present,
        )

    def discover_capabilities(self) -> list[ProviderCapability]:
        return list(self._capabilities)

    def _token(self) -> str | None:
        for key in self._env_keys:
            if val := os.environ.get(key):
                return val
        return None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        token = self._token()
        if token:
            headers[self._auth_header] = f"{self._auth_prefix} {token}".strip()
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        timeout = timeout or self.settings.health_timeout_seconds
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, url, headers=self._headers(), params=params, json=json_body)
            return response

    def authenticate(self) -> bool:
        return self._health_request()

    def _health_request(self) -> bool:
        raise NotImplementedError

    def _invoke(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.configure().enabled:
            return {"success": False, "error": f"{self.provider_id}: not configured — set {self._env_keys}"}
        return self._invoke_capability(capability, params)

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
