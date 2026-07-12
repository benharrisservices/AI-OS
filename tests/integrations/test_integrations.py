"""Integration tests."""

from ai_os.integrations.builtin import register_builtin_providers
from ai_os.integrations.registry import discover_providers, get_provider, health_check_all, list_providers
from ai_os.integrations.models import ProviderStatus


class TestProviderRegistry:
    def test_discover_providers(self) -> None:
        ids = discover_providers()
        assert "ollama" in ids
        assert "openai" in ids
        assert "github" in ids
        assert "filesystem" in ids
        assert len(ids) >= 15

    def test_filesystem_always_available(self) -> None:
        discover_providers()
        fs = get_provider("filesystem")
        assert fs is not None
        health = fs.health_check()
        assert health.status == ProviderStatus.HEALTHY

    def test_unconfigured_provider_graceful(self) -> None:
        discover_providers()
        openai = get_provider("openai")
        assert openai is not None
        health = openai.health_check()
        assert health.status in (ProviderStatus.NOT_CONFIGURED, ProviderStatus.HEALTHY)

    def test_health_check_all(self) -> None:
        results = health_check_all()
        assert len(results) >= 15

    def test_provider_capabilities(self) -> None:
        discover_providers()
        gh = get_provider("github")
        assert gh is not None
        caps = gh.discover_capabilities()
        assert any(c.name == "repos" for c in caps)

    def test_invoke_graceful_failure(self) -> None:
        discover_providers()
        notion = get_provider("notion")
        assert notion is not None
        result = notion.invoke("pages", {})
        assert result["success"] is False or "error" in result

    def test_no_agent_import(self) -> None:
        import ai_os.integrations.builtin as mod
        from pathlib import Path
        source = Path(mod.__file__).read_text()
        assert "ai_os.agent" not in source
