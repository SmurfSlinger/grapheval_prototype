"""Combine resolved sub-question answers into one compound response."""

from __future__ import annotations

from src.models import SubQuestionResult, SubQuestionStopReason


def combine_sub_answers(
    sub_question_results: list[SubQuestionResult],
) -> str:
    """Deterministic concatenation of accepted sub-answers in order."""
    parts: list[str] = []
    for result in sub_question_results:
        if result.stop_reason != SubQuestionStopReason.RESOLVED:
            parts.append(
                f"{result.sub_question_id}. {result.question}\n"
                f"[{result.stop_reason.value}] {result.final_answer}"
            )
        else:
            parts.append(f"{result.sub_question_id}. {result.question}\n{result.final_answer}")
    return "\n\n".join(parts).strip()
