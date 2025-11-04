"""LLM provider abstractions for Ollama and optional OpenAI."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx

try:  # Optional dependency
    import openai  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    openai = None  # type: ignore

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - handled via requirements
    load_dotenv = None  # type: ignore

if load_dotenv is not None:
    # Load local environment configuration if available.
    load_dotenv()


class ProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a request."""


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str

    def __init__(self, timeout_s: float = 45.0) -> None:
        self.timeout_s = timeout_s

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` when provider can be used."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return the raw string completion for ``prompt``."""


class OllamaProvider(BaseProvider):
    """Provider targeting a local Ollama instance."""

    name = "ollama"

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        url: str = "http://localhost:11434",
        timeout_s: float = 45.0,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ) -> None:
        super().__init__(timeout_s=timeout_s)
        self.model = model
        self.url = url.rstrip("/")
        self.temperature = temperature
        self.top_p = top_p

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.url}/api/tags")
                response.raise_for_status()
            return True
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs: Any) -> str:
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
            },
        }
        timeout = kwargs.get("timeout_s", self.timeout_s)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(f"{self.url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        content = data.get("response")
        if not content:
            raise ProviderError("Ollama retornou resposta vazia")
        return str(content)


class OpenAIProvider(BaseProvider):
    """Provider for the OpenAI API (optional)."""

    name = "openai"

    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        timeout_s: float = 45.0,
        temperature: float = 0.2,
        top_p: float = 0.95,
    ) -> None:
        super().__init__(timeout_s=timeout_s)
        self.model = model
        self.temperature = temperature
        self.top_p = top_p

    def is_available(self) -> bool:
        if openai is None:
            return False
        api_key = os.environ.get("OPENAI_API_KEY")
        return bool(api_key)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if openai is None:
            raise ProviderError("Biblioteca openai não instalada")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError("OPENAI_API_KEY não configurada")
        openai.api_key = api_key
        messages = kwargs.get("messages")
        if not messages:
            messages = [
                {"role": "system", "content": kwargs.get("system", "Você é um assistente médico." )},
                {"role": "user", "content": prompt},
            ]
        timeout = kwargs.get("timeout_s", self.timeout_s)
        try:
            response = openai.ChatCompletion.create(  # type: ignore[attr-defined]
                model=kwargs.get("model", self.model),
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                max_tokens=kwargs.get("max_tokens", 1200),
                request_timeout=timeout,
            )
        except Exception as exc:  # pragma: no cover - depends on remote API
            raise ProviderError(str(exc)) from exc
        choices = response.get("choices") or []
        if not choices:
            raise ProviderError("OpenAI não retornou escolhas")
        content = choices[0]["message"]["content"]
        return str(content)


def build_providers(preferred: Optional[str] = None) -> Dict[str, BaseProvider]:
    """Instantiate known providers honoring user preference."""

    providers: Dict[str, BaseProvider] = {}
    ollama = OllamaProvider()
    if ollama.is_available():
        providers[ollama.name] = ollama
    openai_provider = OpenAIProvider()
    if openai_provider.is_available():
        providers[openai_provider.name] = openai_provider

    # Ensure preferred provider (if any) is checked first when available.
    if preferred and preferred in providers:
        preferred_provider = providers[preferred]
        providers = {preferred: preferred_provider, **{k: v for k, v in providers.items() if k != preferred}}
    return providers
