"""Provider registry."""

from __future__ import annotations

from ai_os.integrations.base import ProviderAdapter
from ai_os.integrations.models import ProviderHealth

_REGISTRY: dict[str, ProviderAdapter] = {}


def register_provider(adapter: ProviderAdapter) -> None:
    _REGISTRY[adapter.provider_id] = adapter


def get_provider(provider_id: str) -> ProviderAdapter | None:
    return _REGISTRY.get(provider_id)


def list_providers() -> list[ProviderAdapter]:
    return sorted(_REGISTRY.values(), key=lambda p: p.provider_id)


def discover_providers() -> list[str]:
    from ai_os.integrations.builtin import register_builtin_providers

    register_builtin_providers()
    return list(_REGISTRY.keys())


def health_check_all() -> list[ProviderHealth]:
    discover_providers()
    return [p.health_check() for p in list_providers()]
