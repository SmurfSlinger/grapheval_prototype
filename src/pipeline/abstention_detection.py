"""Detect abstention/no-answer responses vs factual claims."""

from __future__ import annotations

import re

ABSTENTION_PHRASES = (
    "there is no information",
    "no information in the",
    "no information is provided",
    "no evidence found",
    "no evidence available",
    "no evidence states",
    "the provided facts do not contain",
    "the provided kgc facts do not",
    "provided kgc facts do not",
    "kgc does not contain information",
    "does not contain information stating",
    "does not contain information about",
    "not enough information",
    "cannot determine",
    "can't determine",
    "cannot be determined",
    "unable to determine",
    "unable to answer",
    "insufficient information",
    "insufficient evidence",
    "not supported by the provided",
    "the context does not state",
    "the context does not say",
    "not specified in the context",
    "do not have enough information",
    "i do not have enough information",
)


def normalize_answer_text(text: str) -> str:
    return " ".join(text.strip().split())


def is_factual_negation_answer(text: str) -> bool:
    lowered = normalize_answer_text(text).lower()
    meta_markers = (
        "does not contain information",
        "does not state",
        "does not say",
        "no information",
        "cannot determine",
        "provided facts",
        "provided kgc",
        "knowledge graph",
        "insufficient evidence",
    )
    if any(marker in lowered for marker in meta_markers):
        return False
    return bool(
        re.search(
            r"\b(?:did not|does not|do not|was not|were not|is not|are not)\s+[a-z]",
            lowered,
        )
    )


def is_abstention_answer(text: str) -> bool:
    lowered = normalize_answer_text(text).lower()
    if not lowered:
        return False
    if any(phrase in lowered for phrase in ABSTENTION_PHRASES):
        return True
    if is_factual_negation_answer(text):
        return False
    return False
