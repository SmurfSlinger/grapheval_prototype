"""Decompose compound questions into ordered atomic sub-questions."""

from __future__ import annotations

from src.config import PROMPT_QUESTION_DECOMPOSITION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider
from src.models import SubQuestion
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
        prompt = self._template.format(question=question.strip())
        try:
            sub_questions, retries = complete_with_retry(
                self.provider.complete,
                prompt,
                parse_question_split_response,
            )
        except StructuredOutputError as exc:
            raise ValueError(f"Question decomposition failed: {exc}") from exc
        return sub_questions, retries
