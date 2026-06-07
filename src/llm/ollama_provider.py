"""Ollama HTTP provider for local Gemma4 models (text-only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from src.config import DEFAULT_MODEL, OLLAMA_BASE_URL, OLLAMA_REQUEST_TIMEOUT
from src.llm.base import LLMProvider


class OllamaError(Exception):
    """Base error for Ollama provider failures."""


class OllamaConnectionError(OllamaError):
    """Raised when the Ollama server is not reachable."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested model is not installed locally."""


class OllamaTimeoutError(OllamaError):
    """Raised when an Ollama request exceeds the configured timeout."""


class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an unexpected or invalid API response."""


class OllamaProvider(LLMProvider):
    """Call Ollama's /api/generate endpoint with streaming disabled."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        timeout: float = OLLAMA_REQUEST_TIMEOUT,
        *,
        verify_on_init: bool = True,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.generate_url = f"{self.base_url}/api/generate"
        self.timeout = timeout
        if verify_on_init:
            self.check_server(self.base_url, timeout=min(timeout, 10))
            self.check_model_installed(self.model, self.base_url, timeout=min(timeout, 10))

    @staticmethod
    def check_server(base_url: str = OLLAMA_BASE_URL, timeout: float = 10) -> None:
        """Raise if the Ollama server is not reachable."""
        tags_url = f"{base_url.rstrip('/')}/api/tags"
        request = urllib.request.Request(tags_url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout):
                return
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError) or "timed out" in str(exc).lower():
                raise OllamaTimeoutError(
                    f"Ollama server at {base_url} timed out during health check."
                ) from exc
            raise OllamaConnectionError(
                "Ollama server is not running or not reachable at "
                f"{base_url}. Start it with: ollama serve"
            ) from exc

    @staticmethod
    def check_model_installed(
        model: str,
        base_url: str = OLLAMA_BASE_URL,
        timeout: float = 10,
    ) -> None:
        """Raise if the requested model is not present locally."""
        tags_url = f"{base_url.rstrip('/')}/api/tags"
        request = urllib.request.Request(tags_url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError) or "timed out" in str(exc).lower():
                raise OllamaTimeoutError(
                    f"Ollama model check timed out (model={model!r})."
                ) from exc
            raise OllamaConnectionError(
                "Ollama server is not running or not reachable at "
                f"{base_url}. Start it with: ollama serve"
            ) from exc

        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaResponseError(
                f"Ollama /api/tags returned invalid JSON: {raw[:200]}"
            ) from exc

        installed = {item.get("name", "") for item in data.get("models", [])}
        # Ollama may report "gemma4:e2b" or "gemma4:e2b" with tags; match prefix.
        if model not in installed and not any(
            name == model or name.startswith(f"{model}:")
            for name in installed
        ):
            raise OllamaModelNotFoundError(
                f"Model {model!r} is not installed. "
                f"Pull it with: ollama pull {model}"
            )

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.generate_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError) or "timed out" in str(exc).lower():
                raise OllamaTimeoutError(
                    f"Ollama request timed out after {self.timeout}s "
                    f"(model={self.model!r})."
                ) from exc
            raise OllamaConnectionError(
                "Ollama server is not running or not reachable at "
                f"{self.generate_url}. Start it with: ollama serve"
            ) from exc

        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaResponseError(
                f"Ollama returned invalid JSON (model={self.model!r}): {raw[:200]}"
            ) from exc

        if error := data.get("error"):
            lowered = error.lower()
            if "not found" in lowered or "does not exist" in lowered:
                raise OllamaModelNotFoundError(
                    f"Model {self.model!r} is not installed. "
                    f"Pull it with: ollama pull {self.model}"
                )
            raise OllamaResponseError(f"Ollama error (model={self.model!r}): {error}")

        if "response" not in data:
            raise OllamaResponseError(
                f"Ollama response missing 'response' field (model={self.model!r}): "
                f"{raw[:200]}"
            )

        return str(data["response"]).strip()
