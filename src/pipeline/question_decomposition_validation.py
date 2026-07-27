"""Validate that decomposed sub-questions are independently answerable."""

from __future__ import annotations

import re

_WH_WORDS = frozenset(
    {
        "who",
        "what",
        "where",
        "when",
        "why",
        "which",
        "how",
        "whose",
        "whom",
    }
)

_TASK_CUES = frozenset(
    {
        "name",
        "list",
        "identify",
        "find",
        "give",
        "state",
        "describe",
        "explain",
        "determine",
        "provide",
        "tell",
    }
)

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")

# Surface-form compound markers (not KG hop-count). Nested single-clause
# multihop questions lack these and must stay one sub-question.
_COMPOUND_RE = re.compile(
    r"(?i)"
    r"(?:"
    r",\s*and\s+"
    r"|\band\s+(?:who|what|where|when|why|which|how|whose|whom)\b"
    r"|,\s*(?:who|what|where|when|why|which|how|whose|whom)\b"
    r"|;\s*"
    r"|\balso\b"
    r"|\bas well as\b"
    r")"
)


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def looks_like_compound_question(text: str) -> bool:
    """True when the surface question asks multiple separable questions."""
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if cleaned.count("?") >= 2:
        return True
    return bool(_COMPOUND_RE.search(cleaned))


def is_meaningful_subquestion(text: str) -> bool:
    """Return True when ``text`` looks like an independently answerable question/task.

    Rejects WH-only tokens, isolated verbs, bare entities, empty/punctuation-only
    fragments, and other incomplete phrase pieces. Generic — not benchmark-specific.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if not re.search(r"[A-Za-z0-9]", cleaned):
        return False

    words = _words(cleaned)
    if not words:
        return False

    lowered = [w.lower() for w in words]

    # Single token is never a complete question ("Who", "crewed", "Apollo").
    if len(words) == 1:
        return False

    has_wh = any(w in _WH_WORDS for w in lowered)
    has_task = any(w in _TASK_CUES for w in lowered)
    has_qmark = "?" in cleaned

    # Two tokens: allow "Who died?" / "What happened?" style only when WH-led.
    if len(words) == 2:
        return bool(has_wh and lowered[0] in _WH_WORDS)

    # Three or more tokens: require interrogative, explicit task cue, or '?'.
    if has_wh or has_task or has_qmark:
        return True

    # Declarative task-like phrasing with a clear verb marker (ed/ing) and entity.
    if any(w.endswith(("ed", "ing")) for w in lowered):
        return True

    return False


def decomposition_is_valid(original: str, sub_questions: list[str]) -> bool:
    """True when every item is meaningful and count matches question shape.

    Multi-item splits are allowed only for surface-compound questions. Atomic
    or nested single-clause questions must not be expanded into multiple items.
    """
    if not sub_questions:
        return False
    if not all(is_meaningful_subquestion(q) for q in sub_questions):
        return False
    if len(sub_questions) > 1 and not looks_like_compound_question(original):
        return False
    return True
