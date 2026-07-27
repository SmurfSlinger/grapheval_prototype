"""Decompose compound questions into ordered atomic sub-questions."""

from __future__ import annotations

from src.config import PROMPT_QUESTION_DECOMPOSITION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider
from src.models import SubQuestion
from src.pipeline.question_decomposition_validation import decomposition_is_valid
from src.pipeline.structured_output import (
    StructuredOutputError,
    complete_with_retry,
    parse_question_split_response,
)


class QuestionSplitter:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_QUESTION_DECOMPOSITION)

    def split(self, question: str) -> tuple[list[SubQuestion], int]:
        original = question.strip()
        if not original:
            return [SubQuestion(id=1, question=original)], 0

        prompt = self._template.format(question=original)
        try:
            sub_questions, retries = complete_with_retry(
                self.provider.complete,
                prompt,
                parse_question_split_response,
            )
        except StructuredOutputError:
            return [SubQuestion(id=1, question=original)], 0

        texts = [sq.question for sq in sub_questions]
        if not decomposition_is_valid(original, texts):
            return [SubQuestion(id=1, question=original)], retries

        # Preserve original wording for non-compound (atomic / nested) inputs.
        if len(sub_questions) == 1:
            return [SubQuestion(id=1, question=original)], retries

        return sub_questions, retries
