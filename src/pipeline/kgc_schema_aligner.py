"""Align extracted answer claims to the KGc canonical subject/relation schema."""

from __future__ import annotations

from src.models import KgcFact, Triple
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
) -> list[Triple]:
    """Map display-label claims to canonical KGc subject/relation when unambiguous."""
    if not kgc_facts:
        return claims

    return [_align_claim(claim, kgc_facts) for claim in claims]


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


def _align_claim(claim: Triple, kgc_facts: list[KgcFact]) -> Triple:
    if _find_exact_canonical_match(claim, kgc_facts):
        return claim

    match = _find_relation_object_match(claim, kgc_facts)
    if match is None:
        match = _find_unique_object_match(claim, kgc_facts)
    if match is None:
        match = _find_first_stage_engine_schema_match(claim, kgc_facts)
    if match is None:
        match = _find_launch_vehicle_schema_match(claim, kgc_facts)
    if match is None:
        match = _find_launch_site_schema_match(claim, kgc_facts)
    if match is None:
        return claim

    if not relations_polarity_compatible(claim.relation, match.relation):
        return claim

    if (
        claim.subject == match.subject
        and claim.relation == match.relation
        and normalize(claim.object) == normalize(match.object)
    ):
        return claim

    note = _format_alignment_note(claim)
    existing = claim.source_sentence
    source_sentence = f"{note} | {existing}" if existing else note
    return Triple(
        subject=match.subject,
        relation=match.relation,
        object=claim.object,
        source_sentence=source_sentence,
    )
