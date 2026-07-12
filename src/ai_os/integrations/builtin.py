"""Built-in provider adapters with real HTTP integrations."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from ai_os.integrations.base import ProviderAdapter
from ai_os.integrations.http_base import HttpProvider
from ai_os.integrations.models import ProviderCapability, ProviderConfig
from ai_os.integrations.registry import register_provider


class _EnvProvider(ProviderAdapter):
    """Fallback for providers without full HTTP integration."""

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
            keys = ", ".join(self._env_keys) or "none"
            return {"success": False, "error": f"{self.provider_id}: not configured — set {keys}"}
        return {"success": True, "capability": capability, "params": params}


class OllamaProvider(ProviderAdapter):
    provider_id = "ollama"
    name = "Ollama"
    _capabilities = [
        ProviderCapability(name="chat", description="Local LLM inference"),
        ProviderCapability(name="embed", description="Local embeddings"),
        ProviderCapability(name="tags", description="List local models"),
    ]

    def _host(self) -> str:
        return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

    def configure(self) -> ProviderConfig:
        return ProviderConfig(provider_id=self.provider_id, enabled=True, credentials_present=True)

    def _requires_credentials(self) -> bool:
        return False

    def authenticate(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                return client.get(f"{self._host()}/api/tags").status_code == 200
        except Exception:
            return False

    def discover_capabilities(self) -> list[ProviderCapability]:
        return list(self._capabilities)

    def _invoke(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        host = self._host()
        try:
            with httpx.Client(timeout=120.0) as client:
                if capability == "tags":
                    r = client.get(f"{host}/api/tags")
                    r.raise_for_status()
                    models = [m.get("name") for m in r.json().get("models", [])]
                    return {"success": True, "models": models}
                if capability == "chat":
                    r = client.post(
                        f"{host}/api/chat",
                        json={
                            "model": params.get("model", os.environ.get("OLLAMA_DEFAULT_MODEL", "llama3.2")),
                            "messages": params.get("messages", []),
                            "stream": False,
                        },
                    )
                    r.raise_for_status()
                    return {"success": True, "response": r.json()}
                if capability == "embed":
                    r = client.post(
                        f"{host}/api/embeddings",
                        json={"model": params.get("model", "nomic-embed-text"), "prompt": params.get("text", "")},
                    )
                    r.raise_for_status()
                    return {"success": True, "embedding": r.json()}
        except httpx.HTTPStatusError as exc:
            return {"success": False, "error": f"Ollama HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class OpenAIProvider(HttpProvider):
    provider_id = "openai"
    name = "OpenAI"
    _env_keys = ["OPENAI_API_KEY"]
    _capabilities = [
        ProviderCapability(name="chat"),
        ProviderCapability(name="embed"),
        ProviderCapability(name="models", description="List available models"),
    ]

    @property
    def base_url(self) -> str:
        return os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")

    def _health_request(self) -> bool:
        return self._request("GET", "/models").status_code == 200

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        if capability == "models":
            r = self._request("GET", "/models")
            if r.status_code != 200:
                return {"success": False, "error": f"OpenAI: {r.status_code} {r.text[:200]}"}
            return {"success": True, "models": [m["id"] for m in r.json().get("data", [])]}
        if capability == "chat":
            r = self._request(
                "POST",
                "/chat/completions",
                json_body={
                    "model": params.get("model", os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4o")),
                    "messages": params.get("messages", []),
                },
                timeout=120.0,
            )
            if r.status_code != 200:
                return {"success": False, "error": f"OpenAI: {r.status_code} {r.text[:200]}"}
            return {"success": True, "response": r.json()}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class AnthropicProvider(HttpProvider):
    provider_id = "anthropic"
    name = "Anthropic"
    _env_keys = ["ANTHROPIC_API_KEY"]
    base_url = "https://api.anthropic.com/v1"
    _auth_header = "x-api-key"
    _auth_prefix = ""
    _capabilities = [ProviderCapability(name="chat"), ProviderCapability(name="models")]

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        headers["anthropic-version"] = "2023-06-01"
        return headers

    def _health_request(self) -> bool:
        return self._request("GET", "/models").status_code == 200

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        if capability == "models":
            r = self._request("GET", "/models")
            if r.status_code != 200:
                return {"success": False, "error": f"Anthropic: {r.status_code} {r.text[:200]}"}
            return {"success": True, "models": r.json()}
        if capability == "chat":
            r = self._request(
                "POST",
                "/messages",
                json_body={
                    "model": params.get("model", os.environ.get("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514")),
                    "max_tokens": params.get("max_tokens", 1024),
                    "messages": params.get("messages", []),
                },
                timeout=120.0,
            )
            if r.status_code != 200:
                return {"success": False, "error": f"Anthropic: {r.status_code} {r.text[:200]}"}
            return {"success": True, "response": r.json()}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class GeminiProvider(HttpProvider):
    provider_id = "gemini"
    name = "Gemini"
    _env_keys = ["GOOGLE_API_KEY"]
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    _capabilities = [ProviderCapability(name="chat"), ProviderCapability(name="models")]

    def _requires_credentials(self) -> bool:
        return True

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def _health_request(self) -> bool:
        key = self._token()
        if not key:
            return False
        r = self._request("GET", "/models", params={"key": key})
        return r.status_code == 200

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        key = self._token()
        if not key:
            return {"success": False, "error": "Gemini: GOOGLE_API_KEY not set"}
        if capability == "models":
            r = self._request("GET", "/models", params={"key": key})
            if r.status_code != 200:
                return {"success": False, "error": f"Gemini: {r.status_code} {r.text[:200]}"}
            return {"success": True, "models": r.json()}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class OpenRouterProvider(HttpProvider):
    provider_id = "openrouter"
    name = "OpenRouter"
    _env_keys = ["OPENROUTER_API_KEY"]
    base_url = "https://openrouter.ai/api/v1"
    _capabilities = [ProviderCapability(name="chat"), ProviderCapability(name="models")]

    def _health_request(self) -> bool:
        return self._request("GET", "/models").status_code == 200

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        if capability == "models":
            r = self._request("GET", "/models")
            if r.status_code != 200:
                return {"success": False, "error": f"OpenRouter: {r.status_code} {r.text[:200]}"}
            return {"success": True, "models": r.json()}
        if capability == "chat":
            r = self._request(
                "POST",
                "/chat/completions",
                json_body={"model": params.get("model"), "messages": params.get("messages", [])},
                timeout=120.0,
            )
            if r.status_code != 200:
                return {"success": False, "error": f"OpenRouter: {r.status_code} {r.text[:200]}"}
            return {"success": True, "response": r.json()}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class GitHubProvider(HttpProvider):
    provider_id = "github"
    name = "GitHub"
    _env_keys = ["GITHUB_TOKEN"]
    base_url = "https://api.github.com"
    _capabilities = [
        ProviderCapability(name="repos"),
        ProviderCapability(name="issues"),
        ProviderCapability(name="pulls"),
        ProviderCapability(name="user"),
    ]

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        headers["X-GitHub-Api-Version"] = "2022-11-28"
        return headers

    def _health_request(self) -> bool:
        return self._request("GET", "/user").status_code == 200

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        if capability == "user":
            r = self._request("GET", "/user")
            if r.status_code != 200:
                return {"success": False, "error": f"GitHub: {r.status_code} {r.text[:200]}"}
            return {"success": True, "user": r.json()}
        if capability == "repos":
            r = self._request("GET", "/user/repos", params={"per_page": params.get("limit", 10), "sort": "updated"})
            if r.status_code != 200:
                return {"success": False, "error": f"GitHub: {r.status_code} {r.text[:200]}"}
            return {"success": True, "repos": r.json()}
        if capability == "issues":
            owner, repo = params.get("owner"), params.get("repo")
            if not owner or not repo:
                return {"success": False, "error": "GitHub issues: owner and repo required"}
            r = self._request("GET", f"/repos/{owner}/{repo}/issues", params={"state": params.get("state", "open")})
            if r.status_code != 200:
                return {"success": False, "error": f"GitHub: {r.status_code} {r.text[:200]}"}
            return {"success": True, "issues": r.json()}
        if capability == "pulls":
            owner, repo = params.get("owner"), params.get("repo")
            if not owner or not repo:
                return {"success": False, "error": "GitHub pulls: owner and repo required"}
            r = self._request("GET", f"/repos/{owner}/{repo}/pulls")
            if r.status_code != 200:
                return {"success": False, "error": f"GitHub: {r.status_code} {r.text[:200]}"}
            return {"success": True, "pulls": r.json()}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class _GoogleProvider(HttpProvider):
    """Shared Google OAuth token handling."""

    _google_token_keys = ["GOOGLE_ACCESS_TOKEN", "GMAIL_ACCESS_TOKEN"]

    def configure(self) -> ProviderConfig:
        token_present = any(os.environ.get(k) for k in self._google_token_keys)
        oauth_present = any(os.environ.get(k) for k in self._env_keys)
        present = token_present or oauth_present
        return ProviderConfig(
            provider_id=self.provider_id,
            enabled=present,
            credentials_present=token_present,
            settings={"oauth_configured": oauth_present},
        )

    def _google_token(self) -> str | None:
        for key in self._google_token_keys:
            if val := os.environ.get(key):
                return val
        return None

    def _google_headers(self) -> dict[str, str]:
        token = self._google_token()
        if not token:
            raise ValueError("GOOGLE_ACCESS_TOKEN not set — complete OAuth or set token in .env")
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def _google_request(self, url: str) -> httpx.Response:
        with httpx.Client(timeout=self.settings.health_timeout_seconds) as client:
            return client.get(url, headers=self._google_headers())


class GmailProvider(_GoogleProvider):
    provider_id = "gmail"
    name = "Gmail"
    _env_keys = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET"]
    _capabilities = [
        ProviderCapability(name="profile"),
        ProviderCapability(name="messages"),
        ProviderCapability(name="send"),
    ]

    def _health_request(self) -> bool:
        if not self._google_token():
            return False
        r = self._google_request("https://gmail.googleapis.com/gmail/v1/users/me/profile")
        return r.status_code == 200

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            if capability == "profile":
                r = self._google_request("https://gmail.googleapis.com/gmail/v1/users/me/profile")
                if r.status_code != 200:
                    return {"success": False, "error": f"Gmail: {r.status_code} {r.text[:200]}"}
                return {"success": True, "profile": r.json()}
            if capability == "messages":
                limit = params.get("limit", 10)
                r = self._google_request(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={limit}"
                )
                if r.status_code != 200:
                    return {"success": False, "error": f"Gmail: {r.status_code} {r.text[:200]}"}
                return {"success": True, "messages": r.json()}
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class GoogleCalendarProvider(_GoogleProvider):
    provider_id = "google-calendar"
    name = "Google Calendar"
    _env_keys = ["GOOGLE_CALENDAR_CLIENT_ID", "GOOGLE_CALENDAR_CLIENT_SECRET"]
    _capabilities = [
        ProviderCapability(name="calendars"),
        ProviderCapability(name="events"),
    ]

    def _health_request(self) -> bool:
        if not self._google_token():
            return False
        r = self._google_request("https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=1")
        return r.status_code == 200

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            if capability == "calendars":
                r = self._google_request("https://www.googleapis.com/calendar/v3/users/me/calendarList")
                if r.status_code != 200:
                    return {"success": False, "error": f"Calendar: {r.status_code} {r.text[:200]}"}
                return {"success": True, "calendars": r.json()}
            if capability == "events":
                cal_id = params.get("calendar_id", "primary")
                r = self._google_request(
                    f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events?maxResults={params.get('limit', 10)}"
                )
                if r.status_code != 200:
                    return {"success": False, "error": f"Calendar: {r.status_code} {r.text[:200]}"}
                return {"success": True, "events": r.json()}
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class GoogleDriveProvider(_GoogleProvider):
    provider_id = "google-drive"
    name = "Google Drive"
    _env_keys = ["GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET"]
    _capabilities = [
        ProviderCapability(name="about"),
        ProviderCapability(name="files"),
    ]

    def _health_request(self) -> bool:
        if not self._google_token():
            return False
        r = self._google_request("https://www.googleapis.com/drive/v3/about?fields=user")
        return r.status_code == 200

    def _invoke_capability(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            if capability == "about":
                r = self._google_request("https://www.googleapis.com/drive/v3/about?fields=user,storageQuota")
                if r.status_code != 200:
                    return {"success": False, "error": f"Drive: {r.status_code} {r.text[:200]}"}
                return {"success": True, "about": r.json()}
            if capability == "files":
                limit = params.get("limit", 10)
                r = self._google_request(
                    f"https://www.googleapis.com/drive/v3/files?pageSize={limit}&fields=files(id,name,mimeType)"
                )
                if r.status_code != 200:
                    return {"success": False, "error": f"Drive: {r.status_code} {r.text[:200]}"}
                return {"success": True, "files": r.json()}
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        return {"success": False, "error": f"Unsupported capability: {capability}"}


class DeepSeekProvider(HttpProvider):
    provider_id = "deepseek"
    name = "DeepSeek"
    _env_keys = ["DEEPSEEK_API_KEY"]
    base_url = "https://api.deepseek.com/v1"
    _capabilities = [ProviderCapability(name="chat")]

    def _health_request(self) -> bool:
        return self._request("GET", "/models").status_code == 200


class GroqProvider(HttpProvider):
    provider_id = "groq"
    name = "Groq"
    _env_keys = ["GROQ_API_KEY"]
    base_url = "https://api.groq.com/openai/v1"
    _capabilities = [ProviderCapability(name="chat")]

    def _health_request(self) -> bool:
        return self._request("GET", "/models").status_code == 200


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
            if not path.is_file():
                return {"success": False, "error": f"Not a file: {path}"}
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
