"""Project a compound Answer(0) onto ordered sub-questions."""

from __future__ import annotations

from dataclasses import dataclass

from src.config import PROMPT_SUB_ANSWER_PROJECTION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider
from src.models import SubQuestion, SubQuestionInitialAnswer
from src.pipeline.labeled_field_projection import (
    project_labeled_fields,
    validate_projection_faithfulness,
)
from src.pipeline.structured_output import (
    StructuredOutputError,
    complete_with_retry,
    parse_sub_answer_projection_response,
)


@dataclass
class ProjectionTrace:
    method: str
    source: str
    faithfulness_passed: bool
    retry_count: int = 0

    def to_dict(self) -> dict[str, str | bool | int]:
        return {
            "method": self.method,
            "source": self.source,
            "faithfulness_passed": self.faithfulness_passed,
            "retry_count": self.retry_count,
        }


class SubAnswerProjector:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_SUB_ANSWER_PROJECTION)

    def project(
        self,
        original_question: str,
        sub_questions: list[SubQuestion],
        compound_answer_0: str,
        *,
        use_deterministic_labeled_fields: bool = True,
    ) -> tuple[list[SubQuestionInitialAnswer], ProjectionTrace]:
        source = compound_answer_0.strip()
        if use_deterministic_labeled_fields:
            deterministic = project_labeled_fields(source, sub_questions)
            if deterministic is not None and validate_projection_faithfulness(source, deterministic):
                return deterministic, ProjectionTrace(
                    method="deterministic_labeled_fields",
                    source=source,
                    faithfulness_passed=True,
                    retry_count=0,
                )

        sub_lines = "\n".join(f"{sq.id}. {sq.question}" for sq in sub_questions)
        prompt = self._template.format(
            question=original_question.strip(),
            sub_questions=sub_lines,
            compound_answer_0=source,
        )
        expected_ids = [sq.id for sq in sub_questions]
        try:
            answers, retries = complete_with_retry(
                self.provider.complete,
                prompt,
                lambda text: parse_sub_answer_projection_response(text, expected_ids),
            )
        except StructuredOutputError as exc:
            raise ValueError(f"Sub-answer projection failed: {exc}") from exc

        faithfulness = validate_projection_faithfulness(source, answers)
        if not faithfulness:
            raise ValueError(
                "Sub-answer projection failed faithfulness validation: "
                "projected fragments must be grounded in the source Answer(0)."
            )
        return answers, ProjectionTrace(
            method="llm_projector",
            source=source,
            faithfulness_passed=True,
            retry_count=retries,
        )
