"""Generate an initial answer from question and trusted context."""

from __future__ import annotations

from src.config import PROMPT_ANSWER_GENERATION, PROMPT_SUB_QUESTION_ANSWER_GENERATION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider
from src.models import KgcFact
from src.pipeline.kgc_serializer import serialize_kgc_facts


class AnswerGenerator:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_ANSWER_GENERATION)
        self._sub_question_template = load_prompt(PROMPT_SUB_QUESTION_ANSWER_GENERATION)

    def generate(self, question: str, context: str) -> str:
        prompt = self._template.format(question=question, context=context)
        return self.provider.complete(prompt).strip()

    def generate_sub_answer(
        self,
        *,
        question: str,
        trusted_context: str,
        carry_forward_context: str = "",
        working_kgc: list[KgcFact] | None = None,
    ) -> str:
        """Answer one sub-question using original trusted context plus carry-forward."""
        context_parts = [trusted_context.strip()]
        if carry_forward_context.strip():
            context_parts.append(carry_forward_context.strip())
        if working_kgc:
            context_parts.append(
                "Working KGc facts (reference only):\n"
                + serialize_kgc_facts(working_kgc)
            )
        combined_context = "\n\n".join(context_parts)
        prompt = self._sub_question_template.format(
            question=question.strip(),
            context=combined_context,
        )
        return self.provider.complete(prompt).strip()
