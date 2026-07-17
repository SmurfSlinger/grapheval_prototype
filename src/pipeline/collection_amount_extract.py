"""Extract collection-amount phrases without trailing mission clauses."""

from __future__ import annotations

import re

COLLECTION_AMOUNT_BASE = (
    r"[\d.]+\s*(?:kg|kilograms|ounces|oz|lb|pounds)"
    r"(?:\s*\([\d.]+\s*(?:kg|kilograms|lb|pounds)\))?"
)
COLLECTION_MATERIAL_SUFFIX = (
    r"\s+of\s+(?:lunar\s+material|moon\s+rock|lunar\s+samples|"
    r"[a-z]+(?:\s+[a-z]+)?)"
)
COLLECTION_TRAILING_CLAUSE = re.compile(
    r"\s+(?:was|were|is|are|during|according|in total)\b",
    re.IGNORECASE,
)


def extract_collection_amount_phrase(text: str) -> str | None:
    base = re.search(COLLECTION_AMOUNT_BASE, text, flags=re.IGNORECASE)
    if not base:
        return None
    start, end = base.span()
    remainder = text[end:]
    material = re.match(COLLECTION_MATERIAL_SUFFIX, remainder, flags=re.IGNORECASE)
    if material:
        end += material.end()
    phrase = text[start:end].strip()
    trailing = COLLECTION_TRAILING_CLAUSE.search(phrase)
    if trailing:
        phrase = phrase[: trailing.start()].strip()
    return phrase or None
