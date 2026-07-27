"""Shared normalization helpers for KGc claim matching."""

from __future__ import annotations

import re

AUXILIARY_RELATION_PREFIXES = ("is_", "was_", "were_", "be_", "being_", "been_")
ALIGNMENT_PREFIX = "Aligned from:"


def normalize_entity_text(text: str) -> str:
    """Strip harmless terminal sentence punctuation from entity/answer values.

    Removes a single trailing ``.``, ``!``, or ``?`` only when the preceding
    character is a lowercase letter or digit so values like ``Neil Armstrong.``
    collapse to ``Neil Armstrong``, while preserving ``Washington, D.C.``,
    ``John F. Kennedy``, and ``7.5 kg``.
    """
    cleaned = (text or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if len(cleaned) >= 2 and cleaned[-1] in ".!?":
        prev = cleaned[-2]
        if prev.islower() or prev.isdigit():
            cleaned = cleaned[:-1].rstrip()
    return cleaned


def normalize(text: str) -> str:
    text = normalize_entity_text(text).lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s-]", "", text)
    return text.strip()


def normalize_subject_for_dedupe(text: str) -> str:
    """Conservative subject normalization for working-KGc dedupe."""
    norm = normalize(text)
    if norm.startswith("the "):
        norm = norm[4:].strip()
    return norm


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
        "was_launched_from",
    }
)

DATE_RELATIONS = frozenset(
    {
        "occurred_during",
        "occurred_from",
        "occurred_between",
        "dates",
        "date_range",
        "mission_dates",
        "dates_of_mission",
    }
)

# Point-event dates kept separate from mission-interval family.
DATE_POINT_RELATIONS = frozenset(
    {
        "occurred_on",
        "launch_date",
        "landing_date",
        "return_date",
    }
)

CREW_RELATIONS = frozenset(
    {
        "crewed_by",
        "was_crewed_by",
        "crew",
        "crew_members",
        "was_crewmember_on",
    }
)

COLLECTION_RELATIONS = frozenset(
    {
        "collected",
        "collected_lunar_material",
        "lunar_material_collected",
        "amount_collected",
    }
)

PRESIDENT_AT_TIME_RELATIONS = frozenset(
    {
        "president_at_time",
        "president_during",
        "was_president_at_time",
    }
)

EXCLUDED_PRESIDENT_PROXY_RELATIONS = frozenset(
    {
        "spoke_with",
        "fulfilled_goal_set_by",
        "goal_set_by",
        "national_goal_set_by",
        "held_title",
    }
)

DIAGNOSIS_RELATIONS = frozenset(
    {
        "diagnosed_with",
        "has_diagnosis",
        "diagnosis",
        "condition",
        "has_condition",
    }
)

LAB_VALUE_RELATIONS = frozenset(
    {
        "a1c",
        "a1c_value",
        "hemoglobin_a1c",
        "has_a1c",
        "lab_value",
        "measured_value",
    }
)

DISEASE_STAGE_RELATIONS = frozenset(
    {
        "disease_stage",
        "ckd_stage",
        "has_ckd_stage",
        "renal_stage",
        "stage",
        "has_stage",
    }
)

EGFR_RELATIONS = frozenset(
    {
        "egfr",
        "egfr_value",
        "has_egfr",
        "kidney_function_measurement",
        "renal_measurement",
    }
)

DISCONTINUED_MED_RELATIONS = frozenset(
    {
        "discontinued",
        "discontinued_medication",
        "medication_discontinued",
        "stopped",
        "stopped_medication",
    }
)

DISCONTINUATION_REASON_RELATIONS = frozenset(
    {
        "discontinued_because",
        "stopped_because",
        "intolerance_reason",
        "adverse_effect",
        "discontinuation_reason",
    }
)

ACTIVE_MED_RELATIONS = frozenset(
    {
        "active_medication",
        "currently_taking",
        "tolerated",
        "medication_tolerated",
        "taking",
    }
)

DOSE_RELATIONS = frozenset(
    {
        "dose",
        "daily_dose",
        "prescribed_dose",
        "has_dose",
    }
)

DISCUSSED_NOT_STARTED_RELATIONS = frozenset(
    {
        "discussed_not_started",
        "planned_not_started",
        "considered",
        "future_option",
        "discussed",
    }
)

ALLERGY_RELATIONS = frozenset(
    {
        "allergic_to",
        "allergy",
        "medication_allergy",
        "has_allergy",
    }
)

ALLERGIC_REACTION_RELATIONS = frozenset(
    {
        "causes_reaction",
        "allergy_reaction",
        "reaction",
        "allergic_reaction",
    }
)

BIRTHPLACE_RELATIONS = frozenset(
    {
        "born_in",
        "born_at",
        "birthplace",
        "birth_place",
        "place_of_birth",
        "birth_town",
        "birth_city",
    }
)

MANUFACTURER_RELATIONS = frozenset(
    {
        "built_by",
        "manufactured_by",
        "made_by",
        "constructed_by",
        "produced_by",
        "builder",
        "manufacturer",
    }
)

LEADER_RELATIONS = frozenset(
    {
        "led_by",
        "leader",
        "headed_by",
        "governed_by",
        "commanded_by",
        "ruled_by",
    }
)

HEADQUARTERS_RELATIONS = frozenset(
    {
        "headquartered_in",
        "headquarters_in",
        "headquarters",
        "based_in",
    }
)

CONTAINMENT_RELATIONS = frozenset(
    {
        "located_in",
        "situated_in",
        "part_of",
        "contains",
        "within",
        "in_state",
        "in_country",
        "in_region",
    }
)

CAPITAL_RELATIONS = frozenset(
    {
        "capital",
        "capital_of",
        "has_capital",
        "has_capital_in",
        "capital_in",
        "capital_city",
    }
)

# Medication-status families must remain distinct (no unsafe collapse).
MEDICATION_STATUS_EXCLUSIONS: dict[str, frozenset[str]] = {
    "medication_discontinued": ACTIVE_MED_RELATIONS | DISCUSSED_NOT_STARTED_RELATIONS,
    "active_medication": DISCONTINUED_MED_RELATIONS | DISCUSSED_NOT_STARTED_RELATIONS,
    "discussed_not_started": DISCONTINUED_MED_RELATIONS | ACTIVE_MED_RELATIONS,
    "discontinued_medication_with_reason": ACTIVE_MED_RELATIONS
    | DISCUSSED_NOT_STARTED_RELATIONS,
    "active_medication_with_dose": DISCONTINUED_MED_RELATIONS
    | DISCUSSED_NOT_STARTED_RELATIONS,
}

INTENT_RELATION_FAMILIES: dict[str, frozenset[str]] = {
    "occurrence_date": DATE_RELATIONS,
    "crew_members": CREW_RELATIONS,
    "launch_site": LAUNCH_SITE_RELATIONS,
    "launch_vehicle": LAUNCH_VEHICLE_RELATIONS,
    "president_at_time": PRESIDENT_AT_TIME_RELATIONS,
    "collection_amount": COLLECTION_RELATIONS,
    "birthplace": BIRTHPLACE_RELATIONS,
    "manufacturer": MANUFACTURER_RELATIONS,
    "leader": LEADER_RELATIONS,
    "headquarters": HEADQUARTERS_RELATIONS,
    "location_containment": CONTAINMENT_RELATIONS,
    "capital_city": CAPITAL_RELATIONS,
    "diagnosis": DIAGNOSIS_RELATIONS,
    "lab_measurement": LAB_VALUE_RELATIONS,
    "disease_stage": DISEASE_STAGE_RELATIONS,
    "renal_measurement": EGFR_RELATIONS,
    "medication_discontinued": DISCONTINUED_MED_RELATIONS,
    "discontinuation_reason": DISCONTINUATION_REASON_RELATIONS,
    "active_medication": ACTIVE_MED_RELATIONS,
    "medication_dose": DOSE_RELATIONS,
    "discussed_not_started": DISCUSSED_NOT_STARTED_RELATIONS,
    "allergy": ALLERGY_RELATIONS,
    "allergic_reaction": ALLERGIC_REACTION_RELATIONS,
    # Composite intents use the union of their slot families.
    "kidney_status": DISEASE_STAGE_RELATIONS | EGFR_RELATIONS,
    "discontinued_medication_with_reason": DISCONTINUED_MED_RELATIONS
    | DISCONTINUATION_REASON_RELATIONS,
    "active_medication_with_dose": ACTIVE_MED_RELATIONS | DOSE_RELATIONS,
    "allergy_with_reaction": ALLERGY_RELATIONS | ALLERGIC_REACTION_RELATIONS,
}

INTENT_CANONICAL_RELATIONS: dict[str, str] = {
    "occurrence_date": "occurred_during",
    "crew_members": "crewed_by",
    "launch_site": "launched_from",
    "launch_vehicle": "launched_by",
    "president_at_time": "president_at_time",
    "collection_amount": "collected",
    "birthplace": "born_in",
    "manufacturer": "built_by",
    "leader": "led_by",
    "headquarters": "headquartered_in",
    "location_containment": "located_in",
    "capital_city": "capital",
    "diagnosis": "diagnosed_with",
    "lab_measurement": "has_a1c",
    "disease_stage": "has_ckd_stage",
    "renal_measurement": "has_egfr",
    "medication_discontinued": "discontinued_medication",
    "discontinuation_reason": "discontinued_because",
    "active_medication": "active_medication",
    "medication_dose": "daily_dose",
    "discussed_not_started": "discussed_not_started",
    "allergy": "allergic_to",
    "allergic_reaction": "causes_reaction",
    "kidney_status": "has_ckd_stage",
    "discontinued_medication_with_reason": "discontinued_medication",
    "active_medication_with_dose": "active_medication",
    "allergy_with_reaction": "allergic_to",
}

# Slot-level families used for composite claim matching (prevents stage↔eGFR cross-match).
SLOT_RELATION_FAMILIES: dict[str, frozenset[str]] = {
    "disease_stage": DISEASE_STAGE_RELATIONS,
    "renal_measurement": EGFR_RELATIONS,
    "medication_discontinued": DISCONTINUED_MED_RELATIONS,
    "discontinuation_reason": DISCONTINUATION_REASON_RELATIONS,
    "active_medication": ACTIVE_MED_RELATIONS,
    "medication_dose": DOSE_RELATIONS,
    "allergy": ALLERGY_RELATIONS,
    "allergic_reaction": ALLERGIC_REACTION_RELATIONS,
}


def slot_intent_for_relation(relation: str) -> str | None:
    rel = normalize_relation(relation)
    for slot_intent, family in SLOT_RELATION_FAMILIES.items():
        if rel in family:
            return slot_intent
    return None


def canonical_relation_for_intent(intent: str, kgc_facts: list["KgcFact"] | None = None) -> str | None:
    """Return the canonical relation for a question intent."""
    if intent not in INTENT_CANONICAL_RELATIONS:
        return None
    default = INTENT_CANONICAL_RELATIONS[intent]
    if not kgc_facts:
        return default
    family = INTENT_RELATION_FAMILIES.get(intent, frozenset())
    for fact in kgc_facts:
        rel = normalize_relation(fact.relation)
        if rel in family:
            return fact.relation
    return default


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
