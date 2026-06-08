"""Baseline self-correction without triple-level graph feedback."""

from __future__ import annotations

from src.config import PROMPT_SELF_CORRECTION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider


class SelfCorrector:
    """Generic faithfulness check: revise if answer conflicts with context."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_SELF_CORRECTION)

    def correct(self, answer: str, context: str) -> str:
        prompt = self._template.format(context=context, answer=answer)
        return self.provider.complete(prompt).strip()
