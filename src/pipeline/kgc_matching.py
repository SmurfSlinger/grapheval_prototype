"""Shared normalization helpers for KGc claim matching."""

from __future__ import annotations

import re

AUXILIARY_RELATION_PREFIXES = ("is_", "was_", "were_", "be_", "being_", "been_")
ALIGNMENT_PREFIX = "Aligned from:"


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s-]", "", text)
    return text.strip()


def normalize_relation(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"[\s-]+", "_", text)
    text = re.sub(r"[^\w_]", "", text)
    text = re.sub(r"_+", "_", text).strip("_")

    for prefix in AUXILIARY_RELATION_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break

    return re.sub(r"_+", "_", text).strip("_")


NEGATION_PREFIXES = ("does_not_", "not_", "never_", "without_", "no_")


def is_negated_relation(relation: str) -> bool:
    rel = normalize_relation(relation)
    return any(rel.startswith(prefix) for prefix in NEGATION_PREFIXES)


def relations_polarity_compatible(claim_relation: str, fact_relation: str) -> bool:
    """True when claim and KGc relation have the same negation polarity."""
    return is_negated_relation(claim_relation) == is_negated_relation(fact_relation)


def is_schema_aligned_claim(source_sentence: str | None) -> bool:
    return bool(source_sentence and source_sentence.startswith(ALIGNMENT_PREFIX))


ENGINE_OBJECT_MARKERS = ("engine", "engines", "motor", "motors")
ENGINE_POWER_RELATIONS = frozenset(
    {
        "powered_by",
        "used",
        "uses",
        "equipped_with",
        "powered",
        "uses_engine",
        "powered_with",
    }
)

LAUNCH_VEHICLE_RELATIONS = frozenset(
    {
        "launched_by",
        "launched_with",
        "launch_vehicle",
        "launch_rocket",
    }
)

LAUNCH_SITE_RELATIONS = frozenset(
    {
        "launched_from",
        "launched_at",
        "launch_site",
        "launch_location",
    }
)


def is_engine_object(obj: str) -> bool:
    text = normalize(obj)
    return any(marker in text for marker in ENGINE_OBJECT_MARKERS)


def is_engine_power_relation(relation: str) -> bool:
    return normalize_relation(relation) in ENGINE_POWER_RELATIONS


def is_launch_vehicle_relation(relation: str) -> bool:
    return normalize_relation(relation) in LAUNCH_VEHICLE_RELATIONS


def is_launch_site_relation(relation: str) -> bool:
    return normalize_relation(relation) in LAUNCH_SITE_RELATIONS


def is_launch_vehicle_object(obj: str) -> bool:
    text = normalize(obj)
    return any(
        marker in text
        for marker in ("rocket", "saturn", "launch vehicle", "booster")
    )


def relations_equivalent_for_engine_claim(claim_relation: str, fact_relation: str) -> bool:
    claim_rel = normalize_relation(claim_relation)
    fact_rel = normalize_relation(fact_relation)
    if claim_rel == fact_rel:
        return True
    return claim_rel in ENGINE_POWER_RELATIONS and fact_rel in ENGINE_POWER_RELATIONS


def subjects_compatible_first_stage(claim_subject: str, fact_subject: str) -> bool:
    """Match generic first-stage references to canonical launch-vehicle stage subjects."""
    claim_norm = normalize(claim_subject)
    fact_norm = normalize(fact_subject)
    if claim_norm == fact_norm:
        return True

    claim_is_first_stage = (
        claim_norm == "first stage"
        or claim_norm.endswith(" first stage")
        or " first stage" in claim_norm
    )
    fact_is_first_stage = (
        "first stage" in fact_norm
        or "s ic stage" in fact_norm
        or "s ic" in fact_norm
        or "sic stage" in fact_norm
    )
    if claim_is_first_stage and fact_is_first_stage:
        return True

    if claim_is_first_stage and "saturn v" in fact_norm:
        return True

    return False
