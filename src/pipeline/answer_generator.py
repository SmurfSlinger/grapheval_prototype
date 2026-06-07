"""Generate an initial answer from question and trusted context."""

from __future__ import annotations

from src.config import PROMPT_ANSWER_GENERATION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider


class AnswerGenerator:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_ANSWER_GENERATION)

    def generate(self, question: str, context: str) -> str:
        prompt = self._template.format(question=question, context=context)
        return self.provider.complete(prompt).strip()
