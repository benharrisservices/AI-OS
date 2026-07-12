"""Built-in model profiles."""

from ai_os.routing.models import ModelProfile

PROFILES: list[ModelProfile] = [
    ModelProfile(provider_id="ollama", model_id="llama3.2", context_length=8192, is_local=True, latency_score=0.9, cost_score=1.0, reasoning_score=0.6, coding_score=0.6),
    ModelProfile(provider_id="openai", model_id="gpt-4o", context_length=128000, reasoning_score=0.9, coding_score=0.85, latency_score=0.6, cost_score=0.3, supports_multimodal=True, supports_structured_output=True),
    ModelProfile(provider_id="anthropic", model_id="claude-sonnet-4-20250514", context_length=200000, reasoning_score=0.95, coding_score=0.9, latency_score=0.55, cost_score=0.35, supports_structured_output=True),
    ModelProfile(provider_id="gemini", model_id="gemini-2.0-flash", context_length=1000000, reasoning_score=0.85, coding_score=0.8, latency_score=0.7, cost_score=0.5, supports_multimodal=True),
    ModelProfile(provider_id="deepseek", model_id="deepseek-chat", context_length=64000, reasoning_score=0.88, coding_score=0.92, cost_score=0.7),
    ModelProfile(provider_id="groq", model_id="llama-3.3-70b", context_length=128000, latency_score=0.95, cost_score=0.6, reasoning_score=0.75),
    ModelProfile(provider_id="openrouter", model_id="auto", context_length=128000, reasoning_score=0.8, coding_score=0.8, cost_score=0.5),
]


def list_profiles() -> list[ModelProfile]:
    return list(PROFILES)
