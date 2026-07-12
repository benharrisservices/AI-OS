"""HTTP provider integration tests with mocks."""

import os
from unittest.mock import patch

import httpx

from ai_os.integrations.builtin import GitHubProvider, OpenAIProvider, GmailProvider
from ai_os.integrations.models import ProviderStatus


class TestHttpProviders:
    def test_github_health_mock(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/user":
                return httpx.Response(200, json={"login": "testuser"})
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        provider = GitHubProvider()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch.object(provider, "_request") as mock_req:
                mock_req.return_value = httpx.Response(200, json={"login": "testuser"})
                health = provider.health_check()
        assert health.status == ProviderStatus.HEALTHY

    def test_openai_not_configured(self) -> None:
        provider = OpenAIProvider()
        with patch.dict(os.environ, {}, clear=True):
            for key in list(os.environ.keys()):
                if key.startswith("OPENAI"):
                    del os.environ[key]
        health = provider.health_check()
        assert health.status == ProviderStatus.NOT_CONFIGURED

    def test_github_invoke_repos_mock(self) -> None:
        provider = GitHubProvider()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch.object(provider, "_request") as mock_req:
                mock_req.return_value = httpx.Response(200, json=[{"name": "ai-os"}])
                result = provider.invoke("repos", {"limit": 5})
        assert result["success"] is True
        assert result["repos"][0]["name"] == "ai-os"

    def test_gmail_missing_token(self) -> None:
        provider = GmailProvider()
        with patch.dict(os.environ, {"GMAIL_CLIENT_ID": "id", "GMAIL_CLIENT_SECRET": "secret"}, clear=False):
            os.environ.pop("GOOGLE_ACCESS_TOKEN", None)
            health = provider.health_check()
        assert health.status in (ProviderStatus.NOT_CONFIGURED, ProviderStatus.DEGRADED)

    def test_invoke_error_message(self) -> None:
        provider = OpenAIProvider()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
        result = provider.invoke("chat", {})
        assert result["success"] is False
        assert "not configured" in result["error"]
