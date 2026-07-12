"""Model routing tests."""

from ai_os.routing.config import RoutingSettings
from ai_os.routing.models import ModelRequest, RoutingPriority
from ai_os.routing.profiles import list_profiles
from ai_os.routing.router import ModelRouter


class TestModelRouter:
    def test_list_profiles(self) -> None:
        profiles = list_profiles()
        assert len(profiles) >= 7
        assert any(p.provider_id == "ollama" for p in profiles)

    def test_route_default(self) -> None:
        route = ModelRouter().route(ModelRequest(task="summarise document"))
        assert route.provider_id
        assert route.model_id
        assert route.score >= 0

    def test_prefer_local_skips_unconfigured_cloud(self, monkeypatch) -> None:
        """Ollama-only deployment: daily briefing must not route to unconfigured cloud."""
        settings = RoutingSettings(
            prefer_local=True,
            fallback_chain="ollama,anthropic,openai",
        )
        router = ModelRouter(settings=settings)
        monkeypatch.setattr(router, "_healthy_providers", lambda: {"ollama"})
        route = router.route(ModelRequest(task="daily briefing"))
        assert route.provider_id == "ollama"
        assert route.fallback_chain == ["ollama"]

    def test_route_local_priority(self) -> None:
        route = ModelRouter().route(
            ModelRequest(task="quick task", priorities=[RoutingPriority.LOCAL])
        )
        assert route.provider_id == "ollama"

    def test_route_coding_priority(self) -> None:
        route = ModelRouter().route(
            ModelRequest(task="write code", priorities=[RoutingPriority.CODING])
        )
        assert route.score > 0

    def test_manual_override(self) -> None:
        route = ModelRouter().route(
            ModelRequest(override_provider="anthropic", override_model="claude-sonnet")
        )
        assert route.provider_id == "anthropic"
        assert route.metadata.get("override") is True

    def test_fallback_chain(self) -> None:
        route = ModelRouter().route(ModelRequest())
        healthy = ModelRouter()._healthy_providers()
        assert route.fallback_chain
        assert all(p in healthy for p in route.fallback_chain)

    def test_structured_output_filter(self) -> None:
        route = ModelRouter().route(
            ModelRequest(require_structured_output=True, priorities=[RoutingPriority.QUALITY])
        )
        assert route.provider_id in ("openai", "anthropic", "gemini", "ollama", "deepseek", "groq", "openrouter")
