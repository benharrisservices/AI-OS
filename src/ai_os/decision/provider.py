"""Optional LLM provider for enriched reasoning (local-first via Ollama)."""

from __future__ import annotations

import httpx

from ai_os.decision.config import DecisionSettings


class LLMProvider:
    """Provider-agnostic LLM interface. Ollama is the default local backend."""

    def __init__(self, settings: DecisionSettings) -> None:
        self.settings = settings

    def is_available(self) -> bool:
        if not self.settings.use_llm:
            return False
        try:
            url = f"{self.settings.ollama_host.rstrip('/')}/api/tags"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code != 200:
                    return False
                models = [m.get("name", "") for m in response.json().get("models", [])]
                return any(self.settings.llm_model in name for name in models)
        except Exception:
            return False

    def complete(self, prompt: str) -> str | None:
        if not self.is_available():
            return None
        url = f"{self.settings.ollama_host.rstrip('/')}/api/generate"
        payload = {
            "model": self.settings.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.settings.default_temperature},
        }
        try:
            with httpx.Client(timeout=float(self.settings.timeout_seconds)) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json().get("response", "").strip()
        except Exception:
            return None
