"""Built-in provider adapters."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

from ai_os.integrations.base import ProviderAdapter
from ai_os.integrations.models import ProviderCapability, ProviderConfig
from ai_os.integrations.registry import register_provider


class _EnvProvider(ProviderAdapter):
    """Base for env-configured providers."""

    _env_keys: list[str] = []
    _capabilities: list[ProviderCapability] = []

    def configure(self) -> ProviderConfig:
        present = any(os.environ.get(k) for k in self._env_keys)
        return ProviderConfig(
            provider_id=self.provider_id,
            enabled=present or not self._requires_credentials(),
            credentials_present=present,
        )

    def authenticate(self) -> bool:
        return self.configure().credentials_present or not self._requires_credentials()

    def discover_capabilities(self) -> list[ProviderCapability]:
        return list(self._capabilities)

    def _invoke(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.configure().enabled:
            return {"success": False, "error": f"{self.provider_id} not configured"}
        return {"success": True, "capability": capability, "params": params}


class OllamaProvider(_EnvProvider):
    provider_id = "ollama"
    name = "Ollama"
    _env_keys = ["OLLAMA_HOST"]
    _capabilities = [
        ProviderCapability(name="chat", description="Local LLM inference"),
        ProviderCapability(name="embed", description="Local embeddings"),
    ]

    def _requires_credentials(self) -> bool:
        return False

    def authenticate(self) -> bool:
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        try:
            with httpx.Client(timeout=5.0) as client:
                return client.get(f"{host.rstrip('/')}/api/tags").status_code == 200
        except Exception:
            return False


class OpenAIProvider(_EnvProvider):
    provider_id = "openai"
    name = "OpenAI"
    _env_keys = ["OPENAI_API_KEY"]
    _capabilities = [ProviderCapability(name="chat"), ProviderCapability(name="embed")]


class AnthropicProvider(_EnvProvider):
    provider_id = "anthropic"
    name = "Anthropic"
    _env_keys = ["ANTHROPIC_API_KEY"]
    _capabilities = [ProviderCapability(name="chat")]


class GeminiProvider(_EnvProvider):
    provider_id = "gemini"
    name = "Gemini"
    _env_keys = ["GOOGLE_API_KEY"]
    _capabilities = [ProviderCapability(name="chat"), ProviderCapability(name="multimodal")]


class DeepSeekProvider(_EnvProvider):
    provider_id = "deepseek"
    name = "DeepSeek"
    _env_keys = ["DEEPSEEK_API_KEY"]
    _capabilities = [ProviderCapability(name="chat"), ProviderCapability(name="coding")]


class GroqProvider(_EnvProvider):
    provider_id = "groq"
    name = "Groq"
    _env_keys = ["GROQ_API_KEY"]
    _capabilities = [ProviderCapability(name="chat", description="Fast inference")]


class OpenRouterProvider(_EnvProvider):
    provider_id = "openrouter"
    name = "OpenRouter"
    _env_keys = ["OPENROUTER_API_KEY"]
    _capabilities = [ProviderCapability(name="chat", description="Multi-model gateway")]


class GitHubProvider(_EnvProvider):
    provider_id = "github"
    name = "GitHub"
    _env_keys = ["GITHUB_TOKEN"]
    _capabilities = [
        ProviderCapability(name="repos"),
        ProviderCapability(name="issues"),
        ProviderCapability(name="pulls"),
    ]


class NotionProvider(_EnvProvider):
    provider_id = "notion"
    name = "Notion"
    _env_keys = ["NOTION_API_KEY"]
    _capabilities = [ProviderCapability(name="pages"), ProviderCapability(name="databases")]


class SlackProvider(_EnvProvider):
    provider_id = "slack"
    name = "Slack"
    _env_keys = ["SLACK_BOT_TOKEN"]
    _capabilities = [ProviderCapability(name="messages"), ProviderCapability(name="channels")]


class DiscordProvider(_EnvProvider):
    provider_id = "discord"
    name = "Discord"
    _env_keys = ["DISCORD_BOT_TOKEN"]
    _capabilities = [ProviderCapability(name="messages"), ProviderCapability(name="channels")]


class GmailProvider(_EnvProvider):
    provider_id = "gmail"
    name = "Gmail"
    _env_keys = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET"]
    _capabilities = [ProviderCapability(name="send"), ProviderCapability(name="read")]


class GoogleCalendarProvider(_EnvProvider):
    provider_id = "google-calendar"
    name = "Google Calendar"
    _env_keys = ["GOOGLE_CALENDAR_CLIENT_ID"]
    _capabilities = [ProviderCapability(name="events"), ProviderCapability(name="create")]


class GoogleDriveProvider(_EnvProvider):
    provider_id = "google-drive"
    name = "Google Drive"
    _env_keys = ["GOOGLE_DRIVE_CLIENT_ID"]
    _capabilities = [ProviderCapability(name="files"), ProviderCapability(name="upload")]


class FilesystemProvider(ProviderAdapter):
    provider_id = "filesystem"
    name = "Filesystem"

    def configure(self) -> ProviderConfig:
        return ProviderConfig(provider_id=self.provider_id, enabled=True, credentials_present=True)

    def authenticate(self) -> bool:
        return True

    def discover_capabilities(self) -> list[ProviderCapability]:
        return [
            ProviderCapability(name="read"),
            ProviderCapability(name="write"),
            ProviderCapability(name="list"),
        ]

    def _requires_credentials(self) -> bool:
        return False

    def _invoke(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(params.get("path", "."))).expanduser()
        if capability == "read":
            return {"success": True, "content": path.read_text(encoding="utf-8")[:8000]}
        if capability == "list" and path.is_dir():
            return {"success": True, "files": [str(p) for p in sorted(path.iterdir())]}
        return {"success": False, "error": f"Unsupported: {capability}"}


class BrowserProvider(ProviderAdapter):
    provider_id = "browser"
    name = "Browser Automation"

    def configure(self) -> ProviderConfig:
        enabled = os.environ.get("BROWSER_AUTOMATION_ENABLED", "false").lower() == "true"
        return ProviderConfig(provider_id=self.provider_id, enabled=enabled, credentials_present=True)

    def authenticate(self) -> bool:
        return self.configure().enabled

    def discover_capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(name="navigate"), ProviderCapability(name="screenshot")]

    def _requires_credentials(self) -> bool:
        return False

    def _invoke(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        return {"success": False, "error": "Browser automation not enabled. Set BROWSER_AUTOMATION_ENABLED=true"}


def register_builtin_providers() -> None:
    for cls in (
        OllamaProvider, OpenAIProvider, AnthropicProvider, GeminiProvider,
        DeepSeekProvider, GroqProvider, OpenRouterProvider,
        GitHubProvider, NotionProvider, SlackProvider, DiscordProvider,
        GmailProvider, GoogleCalendarProvider, GoogleDriveProvider,
        FilesystemProvider, BrowserProvider,
    ):
        register_provider(cls())
