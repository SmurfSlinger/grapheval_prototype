"""Helpers for tracing which LLM provider backs a pipeline stage."""

from __future__ import annotations

from src.llm.base import LLMProvider


def provider_label(provider: LLMProvider) -> str:
    return type(provider).__name__


def provider_model(provider: LLMProvider) -> str | None:
    model = getattr(provider, "model", None)
    return str(model) if model else None


def provider_trace(provider: LLMProvider) -> dict[str, str | None]:
    return {
        "provider_class": provider_label(provider),
        "model": provider_model(provider),
    }


def prefers_json_structured_output(provider: LLMProvider) -> bool:
    """Real models use JSON triples; CSV is kept for optional experiments."""
    from src.llm.ollama_provider import OllamaProvider

    return isinstance(provider, OllamaProvider)
