"""Question-scoped canonical evaluation frames for deterministic comparison."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.models import KgcFact, Triple
from src.pipeline.composite_claim_slots import (
    doses_equivalent,
    is_composite_intent,
    lab_values_equivalent,
    medication_names_equivalent,
    reactions_equivalent,
    stages_equivalent,
)
from src.pipeline.date_range_normalize import date_intervals_equivalent
from src.pipeline.collection_amount_extract import extract_collection_amount_phrase
from src.pipeline.kgc_matching import (
    EXCLUDED_PRESIDENT_PROXY_RELATIONS,
    INTENT_RELATION_FAMILIES,
    MEDICATION_STATUS_EXCLUSIONS,
    normalize,
    normalize_relation,
    normalize_subject_for_dedupe,
    slot_intent_for_relation,
)

PARTICIPANT_SUBJECT_MARKERS = (
    "armstrong",
    "aldrin",
    "collins",
    "crew",
    "astronaut",
    "and ",
)


@dataclass
class TargetEvaluationFrame:
    raw_subject: str
    raw_relation: str
    raw_object: str
    subject: str
    relation: str
    object: str
    projected: bool = False
    subject_alias_match: bool = False
    relation_family_key: str | None = None


@dataclass
class TargetFrameTrace:
    target_frame_normalizations: int = 0
    relation_family_matches: int = 0
    subject_alias_matches: int = 0
    target_scoped_fact_projections: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "target_frame_normalizations": self.target_frame_normalizations,
            "relation_family_matches": self.relation_family_matches,
            "subject_alias_matches": self.subject_alias_matches,
            "target_scoped_fact_projections": self.target_scoped_fact_projections,
        }


def relation_family_for_intent(intent: str) -> frozenset[str]:
    return INTENT_RELATION_FAMILIES.get(intent, frozenset())


def relation_in_target_family(relation: str, intent: str) -> bool:
    family = relation_family_for_intent(intent)
    if not family:
        return True
    rel = normalize_relation(relation)
    if rel in EXCLUDED_PRESIDENT_PROXY_RELATIONS:
        return False
    excluded = MEDICATION_STATUS_EXCLUSIONS.get(intent, frozenset())
    if rel in excluded:
        return False
    return rel in family


def relations_share_target_family(
    left_relation: str,
    right_relation: str,
    intent: str,
) -> bool:
    # Composite intents: only match within the same attribute slot.
    if is_composite_intent(intent):
        left_slot = slot_intent_for_relation(left_relation)
        right_slot = slot_intent_for_relation(right_relation)
        return bool(left_slot and right_slot and left_slot == right_slot)

    family = relation_family_for_intent(intent)
    if not family:
        return normalize_relation(left_relation) == normalize_relation(right_relation)
    left_rel = normalize_relation(left_relation)
    right_rel = normalize_relation(right_relation)
    excluded = MEDICATION_STATUS_EXCLUSIONS.get(intent, frozenset())
    if left_rel in excluded or right_rel in excluded:
        return False
    return left_rel in family and right_rel in family


def canonical_relation_for_target(relation: str, intent: str, canonical: str | None) -> str:
    # Composite intents keep slot-specific relations (do not collapse to one canonical).
    if is_composite_intent(intent):
        return relation
    if canonical and relation_in_target_family(relation, intent):
        return canonical
    return relation


def normalize_claim_for_target(
    claim: Triple,
    *,
    intent: str,
    primary_subject: str | None,
    canonical_relation: str | None,
    question: str,
    trace: TargetFrameTrace | None = None,
) -> TargetEvaluationFrame:
    subject = _canonical_subject(claim.subject, primary_subject, question)
    relation = canonical_relation_for_target(claim.relation, intent, canonical_relation)
    obj = claim.object
    alias = normalize_subject_for_dedupe(claim.subject) != normalize_subject_for_dedupe(subject)
    if trace:
        trace.target_frame_normalizations += 1
        if alias:
            trace.subject_alias_matches += 1
    return TargetEvaluationFrame(
        raw_subject=claim.subject,
        raw_relation=claim.relation,
        raw_object=claim.object,
        subject=subject,
        relation=relation,
        object=obj,
        subject_alias_match=alias,
        relation_family_key=intent if relation_in_target_family(claim.relation, intent) else None,
    )


def normalize_fact_for_target(
    fact: KgcFact,
    *,
    intent: str,
    primary_subject: str | None,
    canonical_relation: str | None,
    question: str,
    trace: TargetFrameTrace | None = None,
) -> TargetEvaluationFrame | None:
    if not relation_in_target_family(fact.relation, intent):
        return None
    subject = _canonical_subject(fact.subject, primary_subject, question)
    relation = canonical_relation_for_target(fact.relation, intent, canonical_relation)
    alias = normalize_subject_for_dedupe(fact.subject) != normalize_subject_for_dedupe(subject)
    if trace:
        trace.target_frame_normalizations += 1
        if alias:
            trace.subject_alias_matches += 1
    return TargetEvaluationFrame(
        raw_subject=fact.subject,
        raw_relation=fact.relation,
        raw_object=fact.object,
        subject=subject,
        relation=relation,
        object=fact.object,
        subject_alias_match=alias,
        relation_family_key=intent,
    )


def project_fact_for_target(
    fact: KgcFact,
    *,
    intent: str,
    primary_subject: str | None,
    canonical_relation: str | None,
    question: str,
    trace: TargetFrameTrace | None = None,
) -> TargetEvaluationFrame | None:
    if intent != "collection_amount":
        return None
    if not relation_in_target_family(fact.relation, intent):
        return None
    if not _is_participant_subject(fact.subject):
        return None
    if not _evidence_in_mission_context(fact.evidence or "", question):
        return None
    if not primary_subject:
        return None
    canonical = primary_subject
    relation = canonical_relation_for_target(fact.relation, intent, canonical_relation)
    if trace:
        trace.target_scoped_fact_projections += 1
        trace.target_frame_normalizations += 1
    return TargetEvaluationFrame(
        raw_subject=fact.subject,
        raw_relation=fact.relation,
        raw_object=fact.object,
        subject=_canonical_subject(canonical, primary_subject, question),
        relation=relation,
        object=fact.object,
        projected=True,
        relation_family_key=intent,
    )


def build_target_evaluation_facts(
    kgc_facts: list[KgcFact],
    *,
    intent: str,
    primary_subject: str | None,
    canonical_relation: str | None,
    question: str,
    trace: TargetFrameTrace | None = None,
) -> list[TargetEvaluationFrame]:
    frames: list[TargetEvaluationFrame] = []
    seen: set[tuple[str, str, str]] = set()

    for fact in kgc_facts:
        direct = normalize_fact_for_target(
            fact,
            intent=intent,
            primary_subject=primary_subject,
            canonical_relation=canonical_relation,
            question=question,
            trace=trace,
        )
        if direct:
            key = (normalize(direct.subject), normalize_relation(direct.relation), normalize(direct.object))
            if key not in seen:
                seen.add(key)
                frames.append(direct)

        projected = project_fact_for_target(
            fact,
            intent=intent,
            primary_subject=primary_subject,
            canonical_relation=canonical_relation,
            question=question,
            trace=trace,
        )
        if projected:
            key = (normalize(projected.subject), normalize_relation(projected.relation), normalize(projected.object))
            if key not in seen:
                seen.add(key)
                frames.append(projected)

    return frames


def subjects_compatible_for_target(
    left_subject: str,
    right_subject: str,
    *,
    primary_subject: str | None,
    question: str,
) -> bool:
    left = normalize_subject_for_dedupe(left_subject)
    right = normalize_subject_for_dedupe(right_subject)
    if left == right:
        return True

    if _patient_case_ids_match(left, right):
        return True

    primary = normalize_subject_for_dedupe(primary_subject or "")
    question_norm = normalize(question)
    weak = {"chart", "the chart", "patient", "the patient", "context", "record"}
    if primary and ((left in weak and right == primary) or (right in weak and left == primary)):
        return True
    if left in weak and right in weak:
        return True

    def in_question_frame(subject: str) -> bool:
        if primary and (subject == primary or subject.startswith(primary) or primary.startswith(subject)):
            return True
        if primary and _patient_case_ids_match(subject, primary):
            return True
        if "apollo 11" in question_norm and "apollo 11" in subject:
            return True
        if subject == "mission" and primary and "apollo" in primary:
            return True
        if subject == "mission" and "apollo" in question_norm and "mission" in question_norm:
            return True
        if subject.endswith(" mission") and "apollo" in subject and "mission" in question_norm:
            return True
        return False

    return in_question_frame(left) and in_question_frame(right)


def _patient_case_ids_match(left: str, right: str) -> bool:
    pattern = re.compile(r"patient(?:\s+case)?\s+([a-z0-9\-]+)")
    left_ids = pattern.findall(left)
    right_ids = pattern.findall(right)
    if left_ids and right_ids:
        return left_ids[0] == right_ids[0]
    return False


def objects_compatible_for_intent(
    left_object: str,
    right_object: str,
    intent: str,
    *,
    claim_relation: str | None = None,
) -> bool:
    comparison_intent = intent
    if is_composite_intent(intent) and claim_relation:
        comparison_intent = slot_intent_for_relation(claim_relation) or intent

    left = normalize(left_object)
    right = normalize(right_object)
    if left == right:
        return True

    if comparison_intent in {"lab_measurement", "renal_measurement"}:
        return lab_values_equivalent(left_object, right_object)

    if comparison_intent == "disease_stage":
        return stages_equivalent(left_object, right_object)

    if comparison_intent == "medication_dose":
        return doses_equivalent(left_object, right_object)

    if comparison_intent in {
        "medication_discontinued",
        "active_medication",
        "discussed_not_started",
        "allergy",
        "diagnosis",
    }:
        if medication_names_equivalent(left_object, right_object):
            return True
        # Allow containment for diagnosis phrases / allergy names.
        if left in right or right in left:
            return True
        return False

    if comparison_intent in {"discontinuation_reason", "allergic_reaction"}:
        if reactions_equivalent(left_object, right_object):
            return True
        return left in right or right in left

    if left in right or right in left:
        return True

    if comparison_intent == "collection_amount":
        left_core = _collection_object_core(left_object)
        right_core = _collection_object_core(right_object)
        if left_core and right_core:
            return left_core == right_core or left_core in right_core or right_core in left_core

    if comparison_intent == "occurrence_date":
        return _date_objects_overlap(left_object, right_object)

    if comparison_intent == "crew_members":
        return _crew_lists_equivalent(left_object, right_object)

    if comparison_intent == "president_at_time":
        return _president_names_equivalent(left_object, right_object)

    return False


def _president_names_equivalent(left: str, right: str) -> bool:
    def core(name: str) -> str:
        text = normalize(name)
        return re.sub(r"^president\s+", "", text).strip()

    left_core = core(left)
    right_core = core(right)
    return bool(left_core) and left_core == right_core


def objects_conflict_for_intent(
    left_object: str,
    right_object: str,
    intent: str,
    *,
    claim_relation: str | None = None,
) -> bool:
    if objects_compatible_for_intent(
        left_object,
        right_object,
        intent,
        claim_relation=claim_relation,
    ):
        return False
    comparison_intent = intent
    if is_composite_intent(intent) and claim_relation:
        comparison_intent = slot_intent_for_relation(claim_relation) or intent
    if comparison_intent in {
        "collection_amount",
        "occurrence_date",
        "crew_members",
        "launch_site",
        "president_at_time",
        "lab_measurement",
        "disease_stage",
        "renal_measurement",
        "medication_dose",
        "medication_discontinued",
        "discontinuation_reason",
        "active_medication",
        "discussed_not_started",
        "allergy",
        "allergic_reaction",
        "diagnosis",
        "kidney_status",
        "discontinued_medication_with_reason",
        "active_medication_with_dose",
        "allergy_with_reaction",
    }:
        return bool(normalize(left_object) and normalize(right_object))
    return normalize(left_object) != normalize(right_object)


def _canonical_subject(subject: str, primary_subject: str | None, question: str) -> str:
    if primary_subject:
        primary_norm = normalize_subject_for_dedupe(primary_subject)
        subject_norm = normalize_subject_for_dedupe(subject)
        question_norm = normalize(question)
        if subject_norm in {"chart", "the chart", "patient", "the patient", "context", "record"}:
            return primary_subject
        if subject_norm == "mission" and "apollo" in question_norm:
            return primary_subject
        if subject_norm.endswith(" mission") and "apollo" in subject_norm:
            return primary_subject
        if subject_norm == primary_norm or primary_norm.startswith(subject_norm) or subject_norm.startswith(primary_norm):
            return primary_subject
    return subject


def _is_participant_subject(subject: str) -> bool:
    lowered = normalize(subject)
    return any(marker in lowered for marker in PARTICIPANT_SUBJECT_MARKERS)


def _evidence_in_mission_context(evidence: str, question: str) -> bool:
    text = normalize(evidence)
    question_norm = normalize(question)
    markers = ("lunar", "moon", "material", "collect", "apollo")
    return any(marker in text for marker in markers) or any(
        marker in question_norm for marker in ("lunar", "apollo", "material")
    )


def _collection_object_core(text: str) -> str:
    phrase = extract_collection_amount_phrase(text)
    return normalize(phrase) if phrase else normalize(text)


def _date_objects_overlap(left: str, right: str) -> bool:
    left_norm = normalize(left)
    right_norm = normalize(right)
    if left_norm == right_norm:
        return True
    return date_intervals_equivalent(left, right)


def _crew_lists_equivalent(left: str, right: str) -> bool:
    def names(value: str) -> set[str]:
        parts = re.split(r",|\band\b", value.lower())
        cleaned = set()
        for part in parts:
            token = normalize(part.strip())
            if token:
                cleaned.add(token)
        return cleaned

    left_names = names(left)
    right_names = names(right)
    if not left_names or not right_names:
        return False
    return left_names == right_names
