"""Single source of truth for environment variables and provider credentials."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EnvVar:
    key: str
    description: str = ""
    secret: bool = True


@dataclass(frozen=True)
class ProviderEnvSpec:
    provider_id: str
    display_name: str
    credential_keys: tuple[str, ...]
    optional: bool = True
    notes: str = ""


# Core runtime — API starts even when these use defaults.
CORE_ENV: tuple[EnvVar, ...] = (
    EnvVar("AI_OS_DATA_DIR", "Persistent data root", secret=False),
    EnvVar("AI_OS_LOG_LEVEL", "Logging level (debug|info|warn|error)", secret=False),
    EnvVar("PORT", "HTTP listen port (Railway injects this)", secret=False),
    EnvVar("CORS_ORIGINS", "Extra CORS origins (comma-separated)", secret=False),
)

# Optional LLM / integration providers. Missing keys never block startup.
PROVIDER_ENV: tuple[ProviderEnvSpec, ...] = (
    ProviderEnvSpec("openai", "OpenAI", ("OPENAI_API_KEY",)),
    ProviderEnvSpec("anthropic", "Anthropic", ("ANTHROPIC_API_KEY",)),
    ProviderEnvSpec("gemini", "Gemini", ("GOOGLE_API_KEY",)),
    ProviderEnvSpec("groq", "Groq", ("GROQ_API_KEY",)),
    ProviderEnvSpec("deepseek", "DeepSeek", ("DEEPSEEK_API_KEY",)),
    ProviderEnvSpec("openrouter", "OpenRouter", ("OPENROUTER_API_KEY",)),
    ProviderEnvSpec("github", "GitHub", ("GITHUB_TOKEN",)),
    ProviderEnvSpec("ollama", "Ollama", (), notes="Uses OLLAMA_HOST (default http://127.0.0.1:11434)"),
    ProviderEnvSpec("gmail", "Gmail", ("GOOGLE_ACCESS_TOKEN",), notes="OAuth via: ai-os auth google"),
    ProviderEnvSpec("google-calendar", "Google Calendar", ("GOOGLE_ACCESS_TOKEN",)),
    ProviderEnvSpec("google-drive", "Google Drive", ("GOOGLE_ACCESS_TOKEN",)),
    ProviderEnvSpec("notion", "Notion", ("NOTION_API_KEY",)),
    ProviderEnvSpec("slack", "Slack", ("SLACK_BOT_TOKEN",)),
    ProviderEnvSpec("discord", "Discord", ("DISCORD_BOT_TOKEN",)),
)

# Knowledge paths — derived from AI_OS_DATA_DIR when unset (see startup.apply_data_dir_defaults).
KNOWLEDGE_PATH_ENV: tuple[EnvVar, ...] = (
    EnvVar("KNOWLEDGE_RAW_DIR", secret=False),
    EnvVar("KNOWLEDGE_PROCESSED_DIR", secret=False),
    EnvVar("KNOWLEDGE_INDEX_DIR", secret=False),
    EnvVar("VECTOR_STORE_PATH", secret=False),
)


@dataclass
class ProviderEnvStatus:
    provider_id: str
    display_name: str
    configured: bool
    message: str = ""


@dataclass
class EnvReport:
    core: list[tuple[str, bool, str]] = field(default_factory=list)
    providers: list[ProviderEnvStatus] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _has_any(keys: tuple[str, ...]) -> bool:
    return any(os.environ.get(k, "").strip() for k in keys)


def provider_configured(spec: ProviderEnvSpec) -> bool:
    if spec.provider_id == "gmail":
        return _has_any(("GOOGLE_ACCESS_TOKEN", "GMAIL_ACCESS_TOKEN")) or _has_any(
            ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET")
        )
    if spec.provider_id in ("google-calendar", "google-drive"):
        return _has_any(("GOOGLE_ACCESS_TOKEN", "GMAIL_ACCESS_TOKEN"))
    if spec.provider_id == "ollama":
        return True
    if not spec.credential_keys:
        return True
    return _has_any(spec.credential_keys)


def evaluate_env() -> EnvReport:
    report = EnvReport()
    for var in CORE_ENV:
        present = bool(os.environ.get(var.key, "").strip()) or var.key in ("AI_OS_LOG_LEVEL", "PORT")
        report.core.append((var.key, present, var.description))
    for spec in PROVIDER_ENV:
        configured = provider_configured(spec)
        message = "configured" if configured else "not configured"
        if spec.provider_id == "gmail" and _has_any(("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET")):
            if not _has_any(("GOOGLE_ACCESS_TOKEN", "GMAIL_ACCESS_TOKEN")):
                message = "OAuth client set — run: ai-os auth google"
        report.providers.append(
            ProviderEnvStatus(
                provider_id=spec.provider_id,
                display_name=spec.display_name,
                configured=configured,
                message=message,
            )
        )
    return report
