"""Keep extracted claim objects anchored to answer text, not KGc fact values."""

from __future__ import annotations

from src.models import Triple
from src.pipeline.kgc_matching import normalize


def _text_in_answer(text: str, answer: str) -> bool:
    normalized = normalize(text)
    if not normalized:
        return False
    return normalized in normalize(answer)


def ground_claim_objects_in_answer(claims: list[Triple], answer: str) -> list[Triple]:
    """Prefer object values that appear in the answer over KGc-copied values."""
    if not answer.strip():
        return claims

    answer_text = answer.strip()
    grounded: list[Triple] = []
    for claim in claims:
        if _text_in_answer(claim.object, answer_text):
            grounded.append(claim)
            continue

        source = (claim.source_sentence or "").strip()
        if source and _text_in_answer(source, answer_text):
            grounded.append(
                Triple(
                    subject=claim.subject,
                    relation=claim.relation,
                    object=source,
                    source_sentence=source,
                )
            )
            continue

        # Single-claim sub-answers: keep schema mapping but anchor object to answer text.
        if len(claims) == 1:
            grounded.append(
                Triple(
                    subject=claim.subject,
                    relation=claim.relation,
                    object=answer_text,
                    source_sentence=source or answer_text,
                )
            )
            continue

        grounded.append(claim)
    return grounded
