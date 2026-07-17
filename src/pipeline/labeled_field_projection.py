"""Deterministic projection of labeled compound Answer(0) fragments."""

from __future__ import annotations

import re

from src.models import SubQuestion, SubQuestionInitialAnswer
from src.pipeline.composite_claim_slots import extract_ckd_stage, extract_egfr
from src.pipeline.kgc_matching import normalize

LABEL_SPLIT_PATTERN = re.compile(r"\.\s+(?=[A-Za-z][^:]{0,80}:)")

# Label keyword → question keyword cues for semantic field matching.
LABEL_QUESTION_CUES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("diagnosis",), ("diagnosis", "diagnosed")),
    (("a1c",), ("a1c", "hba1c", "hemoglobin")),
    (("kidney", "ckd", "egfr"), ("ckd", "egfr", "kidney", "stage")),
    (("stopped", "discontinued", "medication stopped"), ("discontinu", "stopped", "why")),
    (("tolerated", "current", "active"), ("active", "tolerat", "dose")),
    (("discussed", "not started"), ("discussed", "not been started", "not started")),
    (("allergy", "antibiotic"), ("allerg", "reaction")),
]


def parse_labeled_fields(compound_answer_0: str) -> list[tuple[str, str]]:
    text = compound_answer_0.strip()
    if not text or ":" not in text:
        return []

    segments = LABEL_SPLIT_PATTERN.split(text)
    if len(segments) == 1 and "." in text:
        segments = [part.strip() for part in re.split(r"\.\s+", text) if ":" in part]

    fields: list[tuple[str, str]] = []
    for segment in segments:
        if ":" not in segment:
            continue
        label, value = segment.split(":", 1)
        label = label.strip()
        value = value.strip().rstrip(".")
        if label and value:
            fields.append((label, value))
    return fields


def project_labeled_fields(
    compound_answer_0: str,
    sub_questions: list[SubQuestion],
) -> list[SubQuestionInitialAnswer] | None:
    fields = parse_labeled_fields(compound_answer_0)
    if not fields or not sub_questions:
        return None

    if len(fields) == len(sub_questions):
        return [
            SubQuestionInitialAnswer(sub_question_id=sq.id, answer=value)
            for sq, (_label, value) in zip(sub_questions, fields, strict=True)
        ]

    # Semantic fallback when decomposition splits/merges relative to labels.
    semantic = _project_by_label_semantics(fields, sub_questions)
    if semantic is not None and len(semantic) == len(sub_questions):
        return semantic
    return None


def _project_by_label_semantics(
    fields: list[tuple[str, str]],
    sub_questions: list[SubQuestion],
) -> list[SubQuestionInitialAnswer] | None:
    used_fields: set[int] = set()
    # Kidney-style fields may be reused once for stage and once for eGFR when split.
    reusable_field_uses: dict[int, set[str]] = {}
    answers: list[SubQuestionInitialAnswer] = []

    for sq in sub_questions:
        q = normalize(sq.question)
        best_idx = None
        best_score = 0
        for idx, (label, _value) in enumerate(fields):
            score = _label_question_score(normalize(label), q)
            if score <= 0:
                continue
            label_norm = normalize(label)
            is_kidney_field = any(cue in label_norm for cue in ("kidney", "ckd", "egfr"))
            if idx in used_fields and not is_kidney_field:
                continue
            if is_kidney_field and idx in reusable_field_uses:
                # Already used for this attribute role.
                role = "egfr" if "egfr" in q and "stage" not in q else "stage"
                if role in reusable_field_uses[idx]:
                    continue
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_idx is None or best_score <= 0:
            return None

        label, value = fields[best_idx]
        label_norm = normalize(label)
        is_kidney_field = any(cue in label_norm for cue in ("kidney", "ckd", "egfr"))

        projected_value = value
        if "egfr" in q and "stage" not in q:
            egfr = extract_egfr(value)
            if egfr:
                projected_value = egfr
            if is_kidney_field:
                reusable_field_uses.setdefault(best_idx, set()).add("egfr")
        elif ("stage" in q or "ckd" in q) and "egfr" not in q:
            stage = extract_ckd_stage(value)
            if stage:
                projected_value = f"CKD {stage}"
            if is_kidney_field:
                reusable_field_uses.setdefault(best_idx, set()).add("stage")
        else:
            used_fields.add(best_idx)

        if not is_kidney_field:
            used_fields.add(best_idx)

        answers.append(
            SubQuestionInitialAnswer(sub_question_id=sq.id, answer=projected_value)
        )

    return answers


def _label_question_score(label_norm: str, question_norm: str) -> int:
    score = 0
    for label_cues, question_cues in LABEL_QUESTION_CUES:
        label_hit = any(cue in label_norm for cue in label_cues)
        question_hit = any(cue in question_norm for cue in question_cues)
        if label_hit and question_hit:
            score += 2
            # Prefer tighter matches.
            for cue in label_cues:
                if cue in question_norm:
                    score += 1
    return score


def fragment_grounded_in_source(fragment: str, source: str) -> bool:
    fragment_norm = normalize(fragment)
    source_norm = normalize(source)
    if not fragment_norm:
        return False
    if fragment_norm in source_norm:
        return True
    tokens = [token for token in fragment_norm.split() if token]
    if not tokens:
        return False
    # Allow short derived fragments (e.g. stage/eGFR split from a labeled field).
    return all(token in source_norm for token in tokens)


def validate_projection_faithfulness(
    compound_answer_0: str,
    answers: list[SubQuestionInitialAnswer],
) -> bool:
    return all(
        fragment_grounded_in_source(item.answer, compound_answer_0) for item in answers
    )
