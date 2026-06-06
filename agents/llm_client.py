"""Shared LLM client for Ollama (Llama3) and OpenRouter."""

from __future__ import annotations

import os
import sys

import httpx
from openai import OpenAI

from utils.errors import LLMConnectionError

try:
    import truststore
except ImportError:  # pragma: no cover - optional dependency fallback
    truststore = None

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if truststore is not None:
        truststore.inject_into_ssl()

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_OLLAMA_MODEL = "llama3"
DEFAULT_OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")

MODEL_ALIASES = {
    "google/gemini-2.0-flash-001": "google/gemini-2.5-flash",
    "google/gemini-2.0-flash": "google/gemini-2.5-flash",
    "google/gemini-flash-1.5-8b": "google/gemini-2.5-flash-lite",
}


def _ascii_header(value: str) -> str:
    return value.encode("ascii", errors="ignore").decode("ascii")


class LLMClient:
    """Unified interface for Ollama local models and OpenRouter cloud models."""

    def __init__(
        self,
        provider: str = "ollama",
        api_key: str | None = None,
        model: str | None = None,
        ollama_base: str | None = None,
    ):
        self.provider = provider.lower()
        self.api_key = (api_key or os.environ.get("OPENROUTER_API_KEY", "")).strip()
        self.ollama_base = (ollama_base or OLLAMA_BASE).rstrip("/")

        if self.provider == "ollama":
            self.model = model or DEFAULT_OLLAMA_MODEL
        else:
            self.model = resolve_model(model)

    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        """Generate text completion from prompt."""
        if self.provider == "ollama":
            return self._ollama_generate(prompt, system, max_tokens)
        return self._openrouter_generate(prompt, system, max_tokens)

    def _ollama_generate(self, prompt: str, system: str | None, max_tokens: int) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.1},
        }
        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{self.ollama_base}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError as exc:
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.ollama_base}. "
                "Start Ollama and run: ollama pull llama3"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMConnectionError(f"Ollama error: {exc.response.text[:300]}") from exc

        return (data.get("response") or "").strip()

    def _openrouter_generate(self, prompt: str, system: str | None, max_tokens: int) -> str:
        if not self.api_key:
            raise LLMConnectionError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY or enter it in the sidebar."
            )

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        client = OpenAI(
            base_url=OPENROUTER_BASE,
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": _ascii_header(
                    os.environ.get("OPENROUTER_REFERER", "http://localhost:8501")
                ),
                "X-Title": "NL-to-SQL Analytics Agent",
            },
            http_client=httpx.Client(timeout=httpx.Timeout(120.0)),
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.1,
            )
        except httpx.ConnectError as exc:
            detail = str(exc)
            if "CERTIFICATE_VERIFY_FAILED" in detail:
                detail = (
                    "HTTPS certificate verification failed. Install the updated "
                    "requirements and restart Streamlit so Python can use the Windows "
                    "trusted certificate store."
                )
            raise LLMConnectionError(f"OpenRouter ({self.model}): {detail}") from exc
        except Exception as exc:
            raise LLMConnectionError(f"OpenRouter ({self.model}): {exc}") from exc

        return (response.choices[0].message.content or "").strip()

    def is_available(self) -> tuple[bool, str]:
        """Quick health check for the selected provider."""
        if self.provider == "ollama":
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(f"{self.ollama_base}/api/tags")
                    resp.raise_for_status()
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    if not any(self.model in m for m in models):
                        return False, f"Model '{self.model}' not found. Run: ollama pull {self.model}"
                    return True, "Ollama is running"
            except Exception as exc:
                return False, f"Ollama unavailable: {exc}"
        if not self.api_key:
            return False, "OpenRouter API key not set"
        return True, "OpenRouter API key configured"

    def explain_sql(self, sql: str) -> str:
        """Explain generated SQL in concise plain English."""
        prompt = (
            "Explain this SQL query in plain English. Describe what it selects, "
            "joins, filters, aggregations, and key columns. Keep it concise.\n\n"
            f"SQL:\n{sql}"
        )
        return self.generate(
            prompt,
            system="You are a helpful SQL explainer. Do not output code blocks.",
            max_tokens=500,
        )


def resolve_model(model: str | None) -> str:
    """Resolve outdated OpenRouter aliases to currently preferred model IDs."""
    mid = (model or DEFAULT_OPENROUTER_MODEL).strip()
    return MODEL_ALIASES.get(mid, mid)
