"""Question-target compatibility for atomic sub-question claim evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.models import KgcClaimLabel, KgcEvaluationResult, KgcFact, Triple
from src.pipeline.collection_amount_extract import extract_collection_amount_phrase
from src.pipeline.composite_claim_slots import (
    build_composite_claims,
    extract_a1c,
    is_composite_intent,
)
from src.pipeline.kgc_matching import (
    ALLERGY_RELATIONS,
    ALLERGIC_REACTION_RELATIONS,
    ACTIVE_MED_RELATIONS,
    COLLECTION_RELATIONS,
    CREW_RELATIONS,
    DATE_RELATIONS,
    DIAGNOSIS_RELATIONS,
    DISCONTINUED_MED_RELATIONS,
    DISCONTINUATION_REASON_RELATIONS,
    DISCUSSED_NOT_STARTED_RELATIONS,
    DISEASE_STAGE_RELATIONS,
    DOSE_RELATIONS,
    EGFR_RELATIONS,
    EXCLUDED_PRESIDENT_PROXY_RELATIONS,
    INTENT_CANONICAL_RELATIONS,
    INTENT_RELATION_FAMILIES,
    LAB_VALUE_RELATIONS,
    LAUNCH_SITE_RELATIONS,
    MEDICATION_STATUS_EXCLUSIONS,
    PRESIDENT_AT_TIME_RELATIONS,
    canonical_relation_for_intent,
    normalize,
    normalize_relation,
    normalize_subject_for_dedupe,
)
from src.pipeline.target_frame_normalizer import relation_in_target_family
from src.pipeline.trusted_context_bootstrap import infer_primary_subject_from_context

LABEL_PREFIX_PATTERN = re.compile(
    r"^(?:mission dates|astronauts|launch site|president at the time|"
    r"lunar material collected|president at the time|"
    r"diagnosis|a1c|kidney disease|medication stopped|"
    r"current tolerated medication|discussed but not started|"
    r"antibiotic allergy)\s*:\s*",
    re.IGNORECASE,
)

PATIENT_CASE_PATTERN = re.compile(
    r"\bpatient(?:\s+case)?\s+([a-z0-9\-]+)\b",
    re.IGNORECASE,
)

WEAK_SUBJECTS = frozenset(
    {
        "chart",
        "the chart",
        "patient",
        "the patient",
        "context",
        "record",
        "the record",
        "note",
        "documentation",
    }
)


@dataclass
class QuestionTarget:
    question: str
    intent: str
    expected_relations: frozenset[str] = frozenset()
    excluded_relations: frozenset[str] = frozenset()
    primary_subject: str | None = None
    canonical_relation: str | None = None

    def to_dict(self) -> dict[str, str | list[str] | None]:
        return {
            "question": self.question,
            "intent": self.intent,
            "expected_relations": sorted(self.expected_relations),
            "excluded_relations": sorted(self.excluded_relations),
            "primary_subject": self.primary_subject,
            "canonical_relation": self.canonical_relation,
        }


@dataclass
class TargetEvaluation:
    satisfied: bool
    on_target_supported_count: int = 0
    supported_but_irrelevant_count: int = 0
    unsupported_target_count: int = 0


def relation_matches_target(relation: str, target: QuestionTarget) -> bool:
    if not target.expected_relations:
        return True
    rel = normalize_relation(relation)
    if rel in target.excluded_relations:
        return False
    return relation_in_target_family(relation, target.intent)


def is_atomic_sub_question(question: str) -> bool:
    q = normalize(question)
    if question.count("?") > 1:
        return False

    # Known multi-attribute clinical questions remain atomic.
    if any(
        matcher(q)
        for matcher in (
            _matches_kidney_status,
            _matches_discontinued_with_reason,
            _matches_active_med_with_dose,
            _matches_allergy_with_reaction,
        )
    ):
        return True

    wh_count = len(re.findall(r"\b(what|who|when|where|how|which)\b", q))
    if wh_count > 1:
        return False
    if "," in question and wh_count >= 1 and (
        " and " in q or question.count(",") >= 2
    ):
        return False

    intents = [
        _matches_when_date(q),
        _matches_crew(q),
        _matches_launch_site(q),
        _matches_president_at_time(q),
        _matches_collection_amount(q),
        _matches_diagnosis(q),
        _matches_lab_a1c(q),
        _matches_disease_stage_only(q),
        _matches_egfr_only(q),
        _matches_discontinued_only(q),
        _matches_active_med_only(q),
        _matches_discussed_not_started(q),
        _matches_allergy_only(q),
    ]
    matched = sum(1 for flag in intents if flag)
    if matched == 1:
        return True
    # Single-clause questions with no known intent are still atomic (general).
    if matched == 0 and wh_count <= 1:
        return True
    return False


def derive_question_target(
    question: str,
    kgc_facts: list[KgcFact],
    trusted_context: str | None = None,
) -> QuestionTarget:
    q = normalize(question)
    primary_subject = _infer_primary_subject(kgc_facts, question, trusted_context)

    if not is_atomic_sub_question(question):
        return QuestionTarget(
            question=question,
            intent="compound",
            primary_subject=primary_subject,
        )

    def _build(intent: str, expected: frozenset[str], excluded: frozenset[str] | None = None) -> QuestionTarget:
        return QuestionTarget(
            question=question,
            intent=intent,
            expected_relations=expected,
            excluded_relations=excluded or frozenset(),
            primary_subject=primary_subject,
            canonical_relation=canonical_relation_for_intent(intent, kgc_facts),
        )

    if _matches_when_date(q):
        return _build("occurrence_date", DATE_RELATIONS)
    if _matches_crew(q):
        return _build("crew_members", CREW_RELATIONS)
    if _matches_launch_site(q):
        return _build("launch_site", LAUNCH_SITE_RELATIONS)
    if _matches_president_at_time(q):
        return _build(
            "president_at_time",
            PRESIDENT_AT_TIME_RELATIONS,
            EXCLUDED_PRESIDENT_PROXY_RELATIONS,
        )
    if _matches_collection_amount(q):
        return _build("collection_amount", COLLECTION_RELATIONS)

    if _matches_kidney_status(q):
        return _build(
            "kidney_status",
            DISEASE_STAGE_RELATIONS | EGFR_RELATIONS,
        )
    if _matches_discontinued_with_reason(q):
        return _build(
            "discontinued_medication_with_reason",
            DISCONTINUED_MED_RELATIONS | DISCONTINUATION_REASON_RELATIONS,
            MEDICATION_STATUS_EXCLUSIONS["discontinued_medication_with_reason"],
        )
    if _matches_active_med_with_dose(q):
        return _build(
            "active_medication_with_dose",
            ACTIVE_MED_RELATIONS | DOSE_RELATIONS,
            MEDICATION_STATUS_EXCLUSIONS["active_medication_with_dose"],
        )
    if _matches_allergy_with_reaction(q):
        return _build(
            "allergy_with_reaction",
            ALLERGY_RELATIONS | ALLERGIC_REACTION_RELATIONS,
        )

    if _matches_diagnosis(q):
        return _build("diagnosis", DIAGNOSIS_RELATIONS)
    if _matches_lab_a1c(q):
        return _build("lab_measurement", LAB_VALUE_RELATIONS)
    if _matches_disease_stage_only(q):
        return _build("disease_stage", DISEASE_STAGE_RELATIONS)
    if _matches_egfr_only(q):
        return _build("renal_measurement", EGFR_RELATIONS)
    if _matches_discontinued_only(q):
        return _build(
            "medication_discontinued",
            DISCONTINUED_MED_RELATIONS,
            MEDICATION_STATUS_EXCLUSIONS["medication_discontinued"],
        )
    if _matches_active_med_only(q):
        return _build(
            "active_medication",
            ACTIVE_MED_RELATIONS,
            MEDICATION_STATUS_EXCLUSIONS["active_medication"],
        )
    if _matches_discussed_not_started(q):
        return _build(
            "discussed_not_started",
            DISCUSSED_NOT_STARTED_RELATIONS,
            MEDICATION_STATUS_EXCLUSIONS["discussed_not_started"],
        )
    if _matches_allergy_only(q):
        return _build("allergy", ALLERGY_RELATIONS)

    return QuestionTarget(
        question=question,
        intent="general",
        primary_subject=primary_subject,
    )


def extract_answer_value(answer: str, intent: str | None = None) -> str:
    text = answer.strip()
    text = LABEL_PREFIX_PATTERN.sub("", text).strip()
    text = text.rstrip(".").strip()

    if intent == "launch_site":
        text = re.sub(r"^launched from\s+", "", text, flags=re.IGNORECASE).strip()

    if intent == "collection_amount":
        amount = extract_collection_amount_phrase(text)
        if amount:
            return amount

    if intent == "lab_measurement":
        a1c = extract_a1c(text)
        if a1c:
            return a1c

    if intent == "occurrence_date":
        date_match = re.search(
            r"(?:january|february|march|april|may|june|july|august|september|"
            r"october|november|december)[a-z\s\-–—,0-9]+|\b[a-z]+\s+\d{1,2}"
            r"[\-–—]\s*(?:[a-z]+\s+)?\d{1,2},?\s+\d{4}",
            text,
            flags=re.IGNORECASE,
        )
        if date_match:
            return date_match.group(0).strip()

    if intent == "crew_members":
        crew = re.sub(r"^astronauts\s*:\s*", "", text, flags=re.IGNORECASE).strip()
        return crew

    return text


def condition_claims_to_question(
    claims: list[Triple],
    question: str,
    answer: str,
    target: QuestionTarget,
    kgc_facts: list[KgcFact],
) -> list[Triple]:
    if not target.expected_relations or target.intent == "compound":
        return claims

    subject = target.primary_subject or _infer_primary_subject(kgc_facts, question)
    if not subject and claims:
        subject = claims[0].subject

    if is_composite_intent(target.intent) and subject:
        composite = build_composite_claims(
            answer=answer,
            subject=subject,
            intent=target.intent,
        )
        if composite:
            return composite

    value = extract_answer_value(answer, target.intent)
    if not value:
        return claims

    relation = target.canonical_relation or INTENT_CANONICAL_RELATIONS.get(target.intent)
    if not relation and target.expected_relations:
        relation = sorted(target.expected_relations)[0]

    if not subject or not relation:
        return claims

    return [
        Triple(
            subject=subject,
            relation=relation,
            object=value,
            source_sentence=value,
        )
    ]


def dedupe_minimal_claims(
    claims: list[Triple],
    target: QuestionTarget,
    answer: str,
) -> list[Triple]:
    if not claims:
        return claims

    unique: list[Triple] = []
    seen: set[tuple[str, str, str]] = set()
    for claim in claims:
        key = (
            normalize(claim.subject),
            normalize_relation(claim.relation),
            normalize(claim.object),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(claim)

    if is_composite_intent(target.intent):
        # Keep one claim per relation slot; do not collapse to a single claim.
        by_relation: dict[str, Triple] = {}
        for claim in unique:
            rel = normalize_relation(claim.relation)
            if relation_matches_target(claim.relation, target):
                by_relation.setdefault(rel, claim)
        if by_relation:
            return list(by_relation.values())
        return unique

    if target.intent == "collection_amount" and len(unique) > 1:
        on_target = [
            claim
            for claim in unique
            if relation_matches_target(claim.relation, target)
        ]
        if on_target:
            mission_level = [
                claim
                for claim in on_target
                if "apollo" in normalize(claim.subject)
                or normalize(claim.subject) in normalize(answer)
            ]
            if mission_level:
                return [mission_level[0]]
            return [on_target[0]]

    if target.intent in {
        "occurrence_date",
        "launch_site",
        "crew_members",
        "president_at_time",
        "diagnosis",
        "lab_measurement",
        "discussed_not_started",
    }:
        if len(unique) > 1:
            on_target = [
                claim
                for claim in unique
                if relation_matches_target(claim.relation, target)
            ]
            if on_target:
                return [on_target[0]]

    return unique


def evaluate_target_satisfaction(
    evaluated_claims: list[KgcEvaluationResult],
    target: QuestionTarget,
) -> TargetEvaluation:
    if not target.expected_relations:
        return TargetEvaluation(
            satisfied=True,
            on_target_supported_count=sum(
                1 for ev in evaluated_claims if ev.label == KgcClaimLabel.SUPPORTED
            ),
        )

    on_target_supported = 0
    supported_irrelevant = 0
    unsupported_target = 0

    for ev in evaluated_claims:
        rel = normalize_relation(ev.triple.relation)
        on_target = relation_matches_target(ev.triple.relation, target)
        excluded = rel in target.excluded_relations

        if ev.label == KgcClaimLabel.SUPPORTED:
            if on_target and not excluded:
                on_target_supported += 1
            else:
                supported_irrelevant += 1
        elif on_target and ev.label in (
            KgcClaimLabel.CONTRADICTED,
            KgcClaimLabel.NO_EVIDENCE,
        ):
            unsupported_target += 1

    contradicted = sum(
        1 for ev in evaluated_claims if ev.label == KgcClaimLabel.CONTRADICTED
    )
    no_evidence = sum(
        1 for ev in evaluated_claims if ev.label == KgcClaimLabel.NO_EVIDENCE
    )

    slots_ok = True
    if is_composite_intent(target.intent):
        from src.pipeline.composite_claim_slots import slot_intents_for_composite
        from src.pipeline.kgc_matching import slot_intent_for_relation

        required_slots = set(slot_intents_for_composite(target.intent))
        supported_slots: set[str] = set()
        for ev in evaluated_claims:
            if ev.label != KgcClaimLabel.SUPPORTED:
                continue
            if not relation_matches_target(ev.triple.relation, target):
                continue
            slot = slot_intent_for_relation(ev.triple.relation)
            if slot:
                supported_slots.add(slot)
        slots_ok = bool(required_slots) and required_slots <= supported_slots

    satisfied = (
        on_target_supported >= 1
        and contradicted == 0
        and no_evidence == 0
        and supported_irrelevant == 0
        and slots_ok
    )

    return TargetEvaluation(
        satisfied=satisfied,
        on_target_supported_count=on_target_supported,
        supported_but_irrelevant_count=supported_irrelevant,
        unsupported_target_count=unsupported_target,
    )


def filter_minimal_focused_facts(
    facts: list[KgcFact],
    target: QuestionTarget,
) -> list[KgcFact]:
    if not facts or not target.expected_relations:
        return facts

    question_norm = normalize(target.question)
    primary = normalize_subject_for_dedupe(target.primary_subject or "")

    def score(fact: KgcFact) -> tuple[int, int, int]:
        rel_match = 2 if relation_matches_target(fact.relation, target) else 0
        subject_norm = normalize_subject_for_dedupe(fact.subject)
        subject_match = 0
        if primary and (
            subject_norm == primary
            or subject_norm.endswith(" mission")
            and "apollo" in subject_norm
            or _patient_subjects_compatible(subject_norm, primary)
        ):
            subject_match = 2
        elif "apollo 11" in subject_norm and "apollo 11" in question_norm:
            subject_match = 1
        direct = 1 if fact.evidence and len(fact.evidence) < 120 else 0
        return (rel_match, subject_match, direct)

    ranked = sorted(facts, key=score, reverse=True)
    on_target = [fact for fact in ranked if relation_matches_target(fact.relation, target)]
    # Never inject off-target LLM facts into working KGc when the question has
    # an expected relation family — empty is better than a false on-target signal.
    if not on_target:
        return []

    if is_composite_intent(target.intent):
        # Keep the best fact per relation family slot.
        from src.pipeline.kgc_matching import slot_intent_for_relation

        by_slot: dict[str, KgcFact] = {}
        for fact in on_target:
            slot = slot_intent_for_relation(fact.relation)
            if not slot:
                continue
            by_slot.setdefault(slot, fact)
        return list(by_slot.values())

    best = on_target[0]
    if target.intent in {
        "occurrence_date",
        "launch_site",
        "collection_amount",
        "crew_members",
        "diagnosis",
        "lab_measurement",
        "discussed_not_started",
        "medication_discontinued",
        "active_medication",
        "allergy",
        "disease_stage",
        "renal_measurement",
    }:
        return [best]
    return on_target[:1]


def _infer_primary_subject(
    kgc_facts: list[KgcFact],
    question: str | None = None,
    trusted_context: str | None = None,
) -> str | None:
    from_context = infer_primary_subject_from_context(
        trusted_context or "",
        question,
    )
    if from_context:
        return from_context

    if question:
        raw = re.search(r"\bPatient(?:\s+Case)?\s+[A-Za-z0-9\-]+\b", question)
        if raw:
            return raw.group(0)

    # Prefer patient-case subjects already present in KGc over incidental entities.
    for fact in kgc_facts:
        match = re.search(r"\bPatient(?:\s+Case)?\s+[A-Za-z0-9\-]+\b", fact.subject)
        if match:
            return match.group(0)

    counts: dict[str, int] = {}
    for fact in kgc_facts:
        subject = fact.subject.strip()
        if not subject:
            continue
        if normalize(subject) in WEAK_SUBJECTS:
            continue
        counts[subject] = counts.get(subject, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _patient_subjects_compatible(left: str, right: str) -> bool:
    left_ids = PATIENT_CASE_PATTERN.findall(left)
    right_ids = PATIENT_CASE_PATTERN.findall(right)
    if left_ids and right_ids:
        return left_ids[0].lower() == right_ids[0].lower()
    return False


def _matches_when_date(q: str) -> bool:
    return (
        q.startswith("when ")
        or " when was " in f" {q} "
        or "what date" in q
        or ("date" in q and "mission" in q)
    )


def _matches_crew(q: str) -> bool:
    return (
        "astronaut" in q
        or "crew member" in q
        or ("who were" in q and ("crew" in q or "astronaut" in q))
        or ("who" in q and ("crewed" in q or "crew of" in q))
    )


def _matches_launch_site(q: str) -> bool:
    return (
        ("where" in q and "launch" in q)
        or "launch site" in q
        or "launched from" in q
    )


def _matches_president_at_time(q: str) -> bool:
    return "president" in q and ("time" in q or "at the time" in q)


def _matches_collection_amount(q: str) -> bool:
    return (
        "how much" in q
        or "lunar material" in q
        or ("collected" in q and ("amount" in q or "much" in q or "material" in q))
    )


def _matches_diagnosis(q: str) -> bool:
    return "diagnosis" in q or "diagnosed" in q


def _matches_lab_a1c(q: str) -> bool:
    return "a1c" in q or "hba1c" in q or "hemoglobin a1c" in q


def _matches_kidney_status(q: str) -> bool:
    has_stage = "ckd" in q or "stage" in q or "kidney disease" in q
    has_egfr = "egfr" in q
    return has_stage and has_egfr


def _matches_disease_stage_only(q: str) -> bool:
    if _matches_kidney_status(q):
        return False
    return ("ckd" in q and "stage" in q) or ("stage" in q and "kidney" in q)


def _matches_egfr_only(q: str) -> bool:
    if _matches_kidney_status(q):
        return False
    return "egfr" in q


def _matches_discontinued_with_reason(q: str) -> bool:
    discontinued = "discontinu" in q or "stopped" in q or "stop" in q
    reason = "why" in q or "reason" in q
    return discontinued and reason and "medication" in q


def _matches_discontinued_only(q: str) -> bool:
    if _matches_discontinued_with_reason(q):
        return False
    return ("discontinu" in q or "stopped" in q) and "medication" in q


def _matches_active_med_with_dose(q: str) -> bool:
    active = "active" in q or "tolerat" in q or "currently" in q
    dose = "dose" in q
    return active and dose and "medication" in q


def _matches_active_med_only(q: str) -> bool:
    if _matches_active_med_with_dose(q):
        return False
    return ("active" in q or "tolerat" in q) and "medication" in q


def _matches_discussed_not_started(q: str) -> bool:
    return ("discussed" in q and "not been started" in q) or (
        "discussed" in q and "not started" in q
    ) or ("future" in q and "option" in q and "medication" in q)


def _matches_allergy_with_reaction(q: str) -> bool:
    return "allerg" in q and "reaction" in q


def _matches_allergy_only(q: str) -> bool:
    if _matches_allergy_with_reaction(q):
        return False
    return "allerg" in q
