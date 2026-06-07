"""Abstract LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Swappable LLM backend. Implementations may call local or API models."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return the model's text completion for the given prompt."""
