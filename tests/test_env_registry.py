"""Tests for environment registry."""

from ai_os.env_registry import evaluate_env, provider_configured, PROVIDER_ENV


def test_evaluate_env_runs() -> None:
    report = evaluate_env()
    assert len(report.providers) == len(PROVIDER_ENV)


def test_ollama_always_listed() -> None:
    spec = next(p for p in PROVIDER_ENV if p.provider_id == "ollama")
    assert provider_configured(spec) is True
