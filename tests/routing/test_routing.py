"""Model routing tests."""

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
        assert len(route.fallback_chain) >= 2

    def test_structured_output_filter(self) -> None:
        route = ModelRouter().route(
            ModelRequest(require_structured_output=True, priorities=[RoutingPriority.QUALITY])
        )
        assert route.provider_id in ("openai", "anthropic", "gemini", "ollama", "deepseek", "groq", "openrouter")
