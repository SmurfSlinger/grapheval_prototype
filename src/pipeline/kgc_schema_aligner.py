"""Align extracted answer claims to the KGc canonical subject/relation schema.

Subject and relation may be canonicalized when unambiguous. The claim object is
never replaced with a trusted KGc object — that would hide contradictions.

Safety invariants:
- Never change both subject and relation based only on an object match.
- A relation+object match may canonicalize the subject only when relation
  semantics and direction are already compatible.
- A subject+object match may canonicalize the relation only when entities stay fixed.
- A unique-object match alone must not replace both subject and relation.
- Changing both subject and relation requires an independent, narrowly justified
  generic transform (engine/launch families), not object uniqueness alone.
- Prefer preserving the original claim (later NO_EVIDENCE) over laundering it
  into an unrelated SUPPORTED FACT.
"""

from __future__ import annotations

from src.models import KgcFact, Triple
from src.pipeline.claim_grounding import TripleTransformation
from src.pipeline.debug_log import log_debug_event
from src.pipeline.kgc_matching import (
    ALIGNMENT_PREFIX,
    is_engine_object,
    is_engine_power_relation,
    is_launch_site_relation,
    is_launch_vehicle_object,
    is_launch_vehicle_relation,
    normalize,
    normalize_relation,
    relations_polarity_compatible,
    subjects_compatible_first_stage,
)

_DISPLAY_VALUE_RELATIONS = frozenset(
    {
        "has_value",
        "value",
        "label",
        "labeled_as",
    }
)
_DISPLAY_VALUE_SUBJECT_TOKENS = frozenset(
    {
        "attribute",
        "field",
        "label",
        "slot",
        "value",
    }
)


def _format_alignment_note(original: Triple) -> str:
    return (
        f"{ALIGNMENT_PREFIX} {original.subject} -- {original.relation} --> {original.object}"
    )


def _canonical_triple(fact: KgcFact, *, source_sentence: str | None) -> Triple:
    return Triple(
        subject=fact.subject,
        relation=fact.relation,
        object=fact.object,
        source_sentence=source_sentence,
    )


def _find_unique_object_match(
    claim: Triple,
    kgc_facts: list[KgcFact],
) -> KgcFact | None:
    obj = normalize(claim.object)
    matches = [fact for fact in kgc_facts if normalize(fact.object) == obj]
    compatible = [
        fact
        for fact in matches
        if relations_polarity_compatible(claim.relation, fact.relation)
    ]
    if len(compatible) == 1:
        return compatible[0]
    return None


def _find_relation_object_match(
    claim: Triple,
    kgc_facts: list[KgcFact],
) -> KgcFact | None:
    rel = normalize_relation(claim.relation)
    obj = normalize(claim.object)
    matches = [
        fact
        for fact in kgc_facts
        if normalize_relation(fact.relation) == rel and normalize(fact.object) == obj
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _find_subject_object_match(
    claim: Triple,
    kgc_facts: list[KgcFact],
) -> KgcFact | None:
    subject = normalize(claim.subject)
    obj = normalize(claim.object)
    matches = [
        fact
        for fact in kgc_facts
        if normalize(fact.subject) == subject
        and normalize(fact.object) == obj
        and relations_polarity_compatible(claim.relation, fact.relation)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _find_exact_canonical_match(
    claim: Triple,
    kgc_facts: list[KgcFact],
) -> KgcFact | None:
    subject = normalize(claim.subject)
    relation = normalize_relation(claim.relation)
    obj = normalize(claim.object)
    for fact in kgc_facts:
        if (
            normalize(fact.subject) == subject
            and normalize_relation(fact.relation) == relation
            and normalize(fact.object) == obj
        ):
            return fact
    return None


def align_claims_to_kgc_schema(
    claims: list[Triple],
    kgc_facts: list[KgcFact],
    *,
    question_target=None,
) -> tuple[list[Triple], list[TripleTransformation]]:
    """Map display-label claims to canonical KGc subject/relation when unambiguous.

    Never copies a trusted KGc object into the claim.
    """
    if not kgc_facts:
        return claims, []

    aligned: list[Triple] = []
    traces: list[TripleTransformation] = []
    for claim in claims:
        next_claim, claim_traces = _align_claim(
            claim, kgc_facts, question_target=question_target
        )
        aligned.append(next_claim)
        traces.extend(claim_traces)
    return aligned, traces


def _find_first_stage_engine_schema_match(
    claim: Triple,
    kgc_facts: list[KgcFact],
) -> KgcFact | None:
    """Align generic first-stage engine claims to canonical KGc subject/relation."""
    if not is_engine_object(claim.object) or not is_engine_power_relation(claim.relation):
        return None

    matches = [
        fact
        for fact in kgc_facts
        if is_engine_power_relation(fact.relation)
        and is_engine_object(fact.object)
        and subjects_compatible_first_stage(claim.subject, fact.subject)
        and relations_polarity_compatible(claim.relation, fact.relation)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _find_launch_vehicle_schema_match(
    claim: Triple,
    kgc_facts: list[KgcFact],
) -> KgcFact | None:
    """Align launch-vehicle claims (e.g. was_launched_by) to canonical launched_by facts."""
    if not is_launch_vehicle_relation(claim.relation) or not is_launch_vehicle_object(
        claim.object
    ):
        return None

    matches = [
        fact
        for fact in kgc_facts
        if is_launch_vehicle_relation(fact.relation)
        and relations_polarity_compatible(claim.relation, fact.relation)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _find_launch_site_schema_match(
    claim: Triple,
    kgc_facts: list[KgcFact],
) -> KgcFact | None:
    """Align launch-site claims to the canonical launched_from KGc fact when unambiguous."""
    if not is_launch_site_relation(claim.relation):
        return None

    rel = normalize_relation(claim.relation)
    matches = [
        fact
        for fact in kgc_facts
        if normalize_relation(fact.relation) == rel
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _changes_subject(claim: Triple, match: KgcFact) -> bool:
    return normalize(claim.subject) != normalize(match.subject)


def _changes_relation(claim: Triple, match: KgcFact) -> bool:
    return normalize_relation(claim.relation) != normalize_relation(match.relation)


def _is_display_value_claim(claim: Triple) -> bool:
    relation = normalize_relation(claim.relation)
    subject_tokens = set(normalize(claim.subject).split())
    return (
        relation in _DISPLAY_VALUE_RELATIONS
        and bool(subject_tokens & _DISPLAY_VALUE_SUBJECT_TOKENS)
    )


def _target_blocks_alignment(claim: Triple, match: KgcFact, question_target) -> bool:
    if question_target is None or not question_target.expected_relations:
        return False
    from src.pipeline.target_frame_normalizer import relation_in_target_family

    claim_on_target = relation_in_target_family(claim.relation, question_target.intent)
    match_on_target = relation_in_target_family(match.relation, question_target.intent)
    if claim_on_target and not match_on_target:
        return True
    if claim_on_target and match_on_target:
        if normalize_relation(claim.relation) != normalize_relation(match.relation):
            return True
    return False


def _reject_alignment(
    claim: Triple,
    match: KgcFact,
    *,
    reason: str,
) -> None:
    log_debug_event(
        "schema_alignment",
        "alignment_rejected",
        {
            "reason": reason,
            "claim": {
                "subject": claim.subject,
                "relation": claim.relation,
                "object": claim.object,
            },
            "candidate": {
                "subject": match.subject,
                "relation": match.relation,
                "object": match.object,
            },
        },
    )


def _apply_alignment(
    claim: Triple,
    match: KgcFact,
    *,
    allow_subject_change: bool,
    allow_relation_change: bool,
    reason_subject: str,
    reason_relation: str,
) -> tuple[Triple, list[TripleTransformation]]:
    traces: list[TripleTransformation] = []
    next_subject = match.subject if allow_subject_change else claim.subject
    next_relation = match.relation if allow_relation_change else claim.relation

    if (
        next_subject == claim.subject
        and next_relation == claim.relation
        and normalize(claim.object) == normalize(match.object)
    ):
        return claim, traces

    if normalize(claim.object) != normalize(match.object):
        log_debug_event(
            "schema_alignment",
            "preserved_claim_object",
            {
                "claim_object": claim.object,
                "kgc_object": match.object,
                "reason": "never_copy_trusted_kgc_object_into_claim",
            },
        )

    note = _format_alignment_note(claim)
    existing = claim.source_sentence
    source_sentence = f"{note} | {existing}" if existing else note
    if claim.subject != next_subject:
        traces.append(
            TripleTransformation(
                field="subject",
                before=claim.subject,
                after=next_subject,
                reason=reason_subject,
                source_stage="schema_alignment",
            )
        )
    if claim.relation != next_relation:
        traces.append(
            TripleTransformation(
                field="relation",
                before=claim.relation,
                after=next_relation,
                reason=reason_relation,
                source_stage="schema_alignment",
            )
        )
    for trace in traces:
        log_debug_event("schema_alignment", "field_transformed", trace.to_dict())
    return (
        Triple(
            subject=next_subject,
            relation=next_relation,
            object=claim.object,
            source_sentence=source_sentence,
        ),
        traces,
    )


def _align_claim(
    claim: Triple,
    kgc_facts: list[KgcFact],
    *,
    question_target=None,
) -> tuple[Triple, list[TripleTransformation]]:
    if _find_exact_canonical_match(claim, kgc_facts):
        return claim, []

    # Relation + object match: canonicalize subject only when polarity matches.
    rel_obj = _find_relation_object_match(claim, kgc_facts)
    if rel_obj is not None:
        if _target_blocks_alignment(claim, rel_obj, question_target):
            _reject_alignment(
                claim, rel_obj, reason="target_relation_family_blocks_subject_canonicalization"
            )
            return claim, []
        if not relations_polarity_compatible(claim.relation, rel_obj.relation):
            _reject_alignment(claim, rel_obj, reason="relation_polarity_incompatible")
            return claim, []
        return _apply_alignment(
            claim,
            rel_obj,
            allow_subject_change=True,
            allow_relation_change=False,
            reason_subject="canonicalize_subject_to_relation_object_match",
            reason_relation="canonicalize_relation_to_unique_kgc_match",
        )

    # Subject + object match: canonicalize relation only; entities stay fixed.
    subj_obj = _find_subject_object_match(claim, kgc_facts)
    if subj_obj is not None and _changes_relation(claim, subj_obj):
        if _target_blocks_alignment(claim, subj_obj, question_target):
            _reject_alignment(
                claim, subj_obj, reason="target_relation_family_blocks_relation_canonicalization"
            )
            return claim, []
        return _apply_alignment(
            claim,
            subj_obj,
            allow_subject_change=False,
            allow_relation_change=True,
            reason_subject="canonicalize_subject_to_unique_kgc_match",
            reason_relation="canonicalize_relation_to_subject_object_match",
        )

    # Unique object match alone must not rewrite both subject and relation.
    unique_obj = _find_unique_object_match(claim, kgc_facts)
    if unique_obj is not None:
        subject_change = _changes_subject(claim, unique_obj)
        relation_change = _changes_relation(claim, unique_obj)
        if subject_change and relation_change:
            if _is_display_value_claim(claim):
                return _apply_alignment(
                    claim,
                    unique_obj,
                    allow_subject_change=True,
                    allow_relation_change=True,
                    reason_subject="canonicalize_display_value_subject_to_unique_object",
                    reason_relation="canonicalize_display_value_relation_to_unique_object",
                )
            _reject_alignment(
                claim,
                unique_obj,
                reason="unique_object_match_would_change_subject_and_relation",
            )
        elif subject_change and not relation_change:
            if _target_blocks_alignment(claim, unique_obj, question_target):
                _reject_alignment(
                    claim,
                    unique_obj,
                    reason="target_relation_family_blocks_subject_canonicalization",
                )
                return claim, []
            return _apply_alignment(
                claim,
                unique_obj,
                allow_subject_change=True,
                allow_relation_change=False,
                reason_subject="canonicalize_subject_to_unique_object_same_relation",
                reason_relation="canonicalize_relation_to_unique_kgc_match",
            )
        elif relation_change and not subject_change:
            if _target_blocks_alignment(claim, unique_obj, question_target):
                _reject_alignment(
                    claim,
                    unique_obj,
                    reason="target_relation_family_blocks_relation_canonicalization",
                )
                return claim, []
            return _apply_alignment(
                claim,
                unique_obj,
                allow_subject_change=False,
                allow_relation_change=True,
                reason_subject="canonicalize_subject_to_unique_kgc_match",
                reason_relation="canonicalize_relation_to_unique_object_same_subject",
            )

    # Narrowly justified generic transforms may change subject and relation
    # together because they have independent grounding beyond object uniqueness.
    justified: tuple[KgcFact | None, str] = (None, "")
    engine = _find_first_stage_engine_schema_match(claim, kgc_facts)
    if engine is not None:
        justified = (engine, "narrow_first_stage_engine_schema")
    else:
        launch_vehicle = _find_launch_vehicle_schema_match(claim, kgc_facts)
        if launch_vehicle is not None:
            justified = (launch_vehicle, "narrow_launch_vehicle_schema")
        else:
            launch_site = _find_launch_site_schema_match(claim, kgc_facts)
            if launch_site is not None:
                justified = (launch_site, "narrow_launch_site_schema")

    match, justification = justified
    if match is None:
        return claim, []

    if _target_blocks_alignment(claim, match, question_target):
        _reject_alignment(claim, match, reason="target_relation_family_blocks_justified_transform")
        return claim, []
    if not relations_polarity_compatible(claim.relation, match.relation):
        _reject_alignment(claim, match, reason="relation_polarity_incompatible")
        return claim, []

    subject_change = _changes_subject(claim, match)
    relation_change = _changes_relation(claim, match)
    if subject_change and relation_change and not justification:
        _reject_alignment(
            claim,
            match,
            reason="subject_and_relation_change_without_justified_transform",
        )
        return claim, []

    return _apply_alignment(
        claim,
        match,
        allow_subject_change=True,
        allow_relation_change=True,
        reason_subject=f"canonicalize_subject_via_{justification}",
        reason_relation=f"canonicalize_relation_via_{justification}",
    )
