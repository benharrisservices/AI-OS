"""Providers API — wraps integration registry."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ai_os.api.serialize import to_json
from ai_os.integrations.registry import discover_providers, get_provider, health_check_all, list_providers

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def list_all_providers() -> list:
    discover_providers()
    results = []
    for provider in list_providers():
        config = provider.configure()
        results.append({
            "provider_id": provider.provider_id,
            "name": provider.name,
            "enabled": config.enabled,
            "credentials_present": config.credentials_present,
        })
    return results


@router.get("/health")
def providers_health() -> list:
    discover_providers()
    return [to_json(h) for h in health_check_all()]


@router.get("/{provider_id}/health")
def provider_health(provider_id: str) -> dict:
    discover_providers()
    provider = get_provider(provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    return to_json(provider.health_check())


@router.get("/{provider_id}/capabilities")
def provider_capabilities(provider_id: str) -> list:
    discover_providers()
    provider = get_provider(provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    return [to_json(c) for c in provider.discover_capabilities()]
