"""Provider-agnostic model router with automatic fallback."""

from __future__ import annotations

from ai_os.integrations.registry import discover_providers, get_provider
from ai_os.routing.config import RoutingSettings
from ai_os.routing.models import ModelProfile, ModelRequest, ModelRoute, RoutingPriority
from ai_os.routing.profiles import list_profiles


class ModelRouter:
    """Route model requests based on priorities, availability, and fallback chain."""

    def __init__(self, settings: RoutingSettings | None = None) -> None:
        self.settings = settings or RoutingSettings()
        self._profiles = list_profiles()

    def route(self, request: ModelRequest) -> ModelRoute:
        if request.override_provider:
            return ModelRoute(
                provider_id=request.override_provider,
                model_id=request.override_model or "default",
                score=1.0,
                fallback_chain=self._fallback_chain(),
                metadata={"override": True},
            )

        priorities = list(request.priorities)
        if not priorities and self.settings.prefer_local:
            priorities = [RoutingPriority.LOCAL]

        candidates = self._filter_candidates(request, priorities=priorities)
        if not candidates:
            provider = self.settings.default_provider
            return ModelRoute(
                provider_id=provider,
                model_id="default",
                score=0.0,
                fallback_chain=self._fallback_chain(),
                metadata={"fallback": "default"},
            )

        scored = sorted(
            ((p, self._score(p, request, priorities=priorities)) for p in candidates),
            key=lambda x: x[1],
            reverse=True,
        )
        best, score = scored[0]
        available = self._available_providers()
        chain = [p for p in self._fallback_chain() if p in available]

        return ModelRoute(
            provider_id=best.provider_id,
            model_id=best.model_id,
            score=score,
            fallback_chain=chain,
            metadata={"task": request.task},
        )

    def _filter_candidates(
        self, request: ModelRequest, *, priorities: list[RoutingPriority] | None = None
    ) -> list[ModelProfile]:
        healthy = self._healthy_providers()
        priorities = priorities if priorities is not None else request.priorities
        result = []
        for p in self._profiles:
            if p.provider_id not in healthy:
                continue
            if request.min_context_length and p.context_length < request.min_context_length:
                continue
            if request.require_structured_output and not p.supports_structured_output:
                continue
            if request.require_multimodal and not p.supports_multimodal:
                continue
            if RoutingPriority.LOCAL in priorities and not p.is_local:
                continue
            result.append(p)
        return result or [p for p in self._profiles if p.provider_id in healthy]

    def _score(
        self,
        profile: ModelProfile,
        request: ModelRequest,
        *,
        priorities: list[RoutingPriority] | None = None,
    ) -> float:
        priorities = priorities if priorities is not None else request.priorities
        if not priorities:
            return (profile.reasoning_score + profile.coding_score) / 2
        scores: list[float] = []
        for priority in priorities:
            if priority == RoutingPriority.LATENCY:
                scores.append(profile.latency_score)
            elif priority == RoutingPriority.COST:
                scores.append(profile.cost_score)
            elif priority == RoutingPriority.CODING:
                scores.append(profile.coding_score)
            elif priority == RoutingPriority.REASONING:
                scores.append(profile.reasoning_score)
            elif priority == RoutingPriority.LOCAL:
                scores.append(1.0 if profile.is_local else 0.0)
            elif priority == RoutingPriority.QUALITY:
                scores.append((profile.reasoning_score + profile.coding_score) / 2)
        return sum(scores) / len(scores) if scores else 0.5

    def _fallback_chain(self) -> list[str]:
        return [p.strip() for p in self.settings.fallback_chain.split(",") if p.strip()]

    def _healthy_providers(self) -> set[str]:
        discover_providers()
        healthy: set[str] = set()
        for pid in self._fallback_chain():
            provider = get_provider(pid)
            if provider and provider.health_check().status.value == "healthy":
                healthy.add(pid)
        return healthy

    def _available_providers(self) -> set[str]:
        return self._healthy_providers()
