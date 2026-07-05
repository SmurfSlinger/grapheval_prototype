"""Generate a graph-grounded answer using serialized KGc facts."""

from __future__ import annotations

from src.config import PROMPT_KG_ANSWER_GENERATION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider


class KgAnswerGenerator:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_KG_ANSWER_GENERATION)

    def generate(self, question: str, serialized_kgc: str) -> str:
        prompt = self._template.format(question=question, kgc_facts=serialized_kgc)
        return self.provider.complete(prompt).strip()
