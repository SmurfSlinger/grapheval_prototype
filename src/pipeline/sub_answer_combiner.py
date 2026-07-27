"""Combine resolved sub-question answers into one compound response."""

from __future__ import annotations

from typing import Any

from src.models import SubQuestionResult, SubQuestionStopReason
from src.pipeline.kgc_matching import normalize, normalize_entity_text


def prefer_terminal_object_answer(
    answer: str,
    evidence_path: dict[str, Any] | None,
    *,
    path_complete: bool = False,
) -> str:
    """Prefer the evidence-path terminal object when the answer elaborates it.

    Keeps already-atomic answers unchanged. Only rewrites when a complete path
    provides a terminal object that appears inside a longer answer string.
    """
    cleaned = normalize_entity_text(answer)
    if not path_complete or not evidence_path:
        return cleaned

    terminal = evidence_path.get("terminal_claim") or {}
    obj = normalize_entity_text(str(terminal.get("object") or ""))
    if not obj:
        edges = evidence_path.get("evidence_path") or []
        if edges and isinstance(edges[-1], dict):
            obj = normalize_entity_text(str(edges[-1].get("object") or ""))
    if not obj:
        return cleaned

    ans_norm = normalize(cleaned)
    obj_norm = normalize(obj)
    if not obj_norm:
        return cleaned
    if ans_norm == obj_norm:
        return obj
    if obj_norm in ans_norm and ans_norm != obj_norm:
        return obj
    return cleaned


def combine_sub_answers(
    sub_question_results: list[SubQuestionResult],
) -> str:
    """Deterministic concatenation of accepted sub-answers in order."""
    if not sub_question_results:
        return ""

    def _answer(result: SubQuestionResult) -> str:
        return prefer_terminal_object_answer(
            result.final_answer,
            result.evidence_path,
            path_complete=bool(result.evidence_path_complete),
        )

    if (
        len(sub_question_results) == 1
        and sub_question_results[0].stop_reason == SubQuestionStopReason.RESOLVED
    ):
        return _answer(sub_question_results[0])

    if all(
        result.stop_reason == SubQuestionStopReason.RESOLVED
        for result in sub_question_results
    ):
        return "\n\n".join(_answer(result) for result in sub_question_results).strip()

    parts: list[str] = []
    for result in sub_question_results:
        answer = _answer(result)
        if result.stop_reason != SubQuestionStopReason.RESOLVED:
            parts.append(
                f"{result.sub_question_id}. {result.question}\n"
                f"[{result.stop_reason.value}] {answer}"
            )
        else:
            parts.append(f"{result.sub_question_id}. {result.question}\n{answer}")
    return "\n\n".join(parts).strip()
