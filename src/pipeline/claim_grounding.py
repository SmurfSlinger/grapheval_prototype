"""Keep extracted claim objects anchored to answer text, not KGc fact values.

Grounding must not broaden a precise atomic object into an entire sentence when
the atomic value is already a faithful claim object. Every mutation is recorded
in a transformation trace.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.models import Triple
from src.pipeline.debug_log import log_debug_event
from src.pipeline.kgc_matching import normalize


@dataclass
class TripleTransformation:
    field: str
    before: str
    after: str
    reason: str
    source_stage: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text_in_answer(text: str, answer: str) -> bool:
    normalized = normalize(text)
    if not normalized:
        return False
    return normalized in normalize(answer)


def _is_atomic_object(text: str) -> bool:
    """Heuristic: short entity-like values should not be replaced by full sentences."""
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if len(cleaned) > 80:
        return False
    if "\n" in cleaned:
        return False
    # Multi-clause prose is not atomic.
    if cleaned.count(".") >= 1 and len(cleaned.split()) > 6:
        return False
    if cleaned.count(",") >= 2 and len(cleaned.split()) > 8:
        return False
    return True


def _record_transform(
    traces: list[TripleTransformation],
    *,
    field: str,
    before: str,
    after: str,
    reason: str,
) -> None:
    if before == after:
        return
    trace = TripleTransformation(
        field=field,
        before=before,
        after=after,
        reason=reason,
        source_stage="claim_grounding",
    )
    traces.append(trace)
    log_debug_event(
        "claim_grounding",
        "object_transformed",
        trace.to_dict(),
    )


def ground_claim_objects_in_answer(
    claims: list[Triple],
    answer: str,
) -> tuple[list[Triple], list[TripleTransformation]]:
    """Prefer object values that appear in the answer over KGc-copied values.

    Returns grounded claims and the transformation trace for this stage.
    """
    traces: list[TripleTransformation] = []
    if not answer.strip():
        return claims, traces

    answer_text = answer.strip()
    grounded: list[Triple] = []
    for claim in claims:
        original_object = claim.object
        if _text_in_answer(claim.object, answer_text):
            grounded.append(claim)
            continue

        source = (claim.source_sentence or "").strip()

        # Preserve a precise atomic object when the answer still contains it under
        # a looser substring match that normalize() missed, or when broadening
        # would replace it with a full sentence without necessity.
        if _is_atomic_object(claim.object) and claim.object.strip() in answer_text:
            grounded.append(claim)
            continue

        if source and _text_in_answer(source, answer_text):
            if _is_atomic_object(source):
                _record_transform(
                    traces,
                    field="object",
                    before=original_object,
                    after=source,
                    reason="replace_ungrounded_object_with_atomic_source_sentence",
                )
                grounded.append(
                    Triple(
                        subject=claim.subject,
                        relation=claim.relation,
                        object=source,
                        source_sentence=source,
                    )
                )
                continue
            # Source is broader prose; keep atomic claim object for contradiction
            # detection rather than copying the whole sentence into object.
            if _is_atomic_object(claim.object):
                grounded.append(claim)
                continue
            _record_transform(
                traces,
                field="object",
                before=original_object,
                after=source,
                reason="replace_nonatomic_ungrounded_object_with_source_sentence",
            )
            grounded.append(
                Triple(
                    subject=claim.subject,
                    relation=claim.relation,
                    object=source,
                    source_sentence=source,
                )
            )
            continue

        # Single-claim sub-answers: prefer an atomic answer text when the extracted
        # object is ungrounded (typical KGc leak). Never broaden a precise atomic
        # object into a long answer sentence.
        if len(claims) == 1:
            if _is_atomic_object(answer_text):
                _record_transform(
                    traces,
                    field="object",
                    before=original_object,
                    after=answer_text,
                    reason="replace_ungrounded_object_with_atomic_answer",
                )
                grounded.append(
                    Triple(
                        subject=claim.subject,
                        relation=claim.relation,
                        object=answer_text,
                        source_sentence=source or answer_text,
                    )
                )
                continue
            if _is_atomic_object(claim.object):
                grounded.append(claim)
                continue
            _record_transform(
                traces,
                field="object",
                before=original_object,
                after=answer_text,
                reason="anchor_single_nonatomic_claim_to_answer_text",
            )
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
    return grounded, traces
