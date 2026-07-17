"""Deterministic trusted-context fact bootstrap for known question targets.

Extracts target-form facts from trusted context text using reusable patterns.
Does not hard-code case-specific values (patient IDs, drug names, lab numbers).
"""

from __future__ import annotations

import re
from typing import Any

from src.models import KgcFact
from src.pipeline.composite_claim_slots import (
    extract_a1c,
    extract_ckd_stage,
    extract_dose,
    extract_egfr,
)
from src.pipeline.kgc_matching import INTENT_CANONICAL_RELATIONS, normalize


PATIENT_CASE_IN_TEXT = re.compile(
    r"\b(Patient(?:\s+Case)?\s+[A-Za-z0-9\-]+)\b"
)


def infer_primary_subject_from_context(
    trusted_context: str,
    question: str | None = None,
) -> str | None:
    if question:
        match = PATIENT_CASE_IN_TEXT.search(question)
        if match:
            return match.group(1)
    match = PATIENT_CASE_IN_TEXT.search(trusted_context or "")
    if match:
        return match.group(1)
    return None


def bootstrap_facts_from_context(
    *,
    trusted_context: str,
    target: Any,
) -> list[KgcFact]:
    """Return zero or more on-target facts grounded in trusted context text."""
    context = trusted_context.strip()
    expected = getattr(target, "expected_relations", None) or frozenset()
    if not context or not expected:
        return []

    subject = (
        getattr(target, "primary_subject", None)
        or infer_primary_subject_from_context(context, getattr(target, "question", None))
        or "Patient"
    )
    intent = getattr(target, "intent", "general")
    facts: list[KgcFact] = []

    if intent == "diagnosis":
        fact = _diagnosis_fact(subject, context)
        if fact:
            facts.append(fact)
    elif intent == "lab_measurement":
        fact = _a1c_fact(subject, context)
        if fact:
            facts.append(fact)
    elif intent == "disease_stage":
        fact = _stage_fact(subject, context)
        if fact:
            facts.append(fact)
    elif intent == "renal_measurement":
        fact = _egfr_fact(subject, context)
        if fact:
            facts.append(fact)
    elif intent == "kidney_status":
        stage = _stage_fact(subject, context)
        egfr = _egfr_fact(subject, context)
        if stage:
            facts.append(stage)
        if egfr:
            facts.append(egfr)
    elif intent in {"medication_discontinued", "discontinued_medication_with_reason"}:
        facts.extend(_discontinued_facts(subject, context, intent))
    elif intent in {"active_medication", "active_medication_with_dose"}:
        facts.extend(_active_med_facts(subject, context, intent))
    elif intent == "discussed_not_started":
        fact = _discussed_fact(subject, context)
        if fact:
            facts.append(fact)
    elif intent in {"allergy", "allergy_with_reaction"}:
        facts.extend(_allergy_facts(subject, context, intent))
    elif intent == "occurrence_date":
        fact = _mission_date_fact(subject, context)
        if fact:
            facts.append(fact)

    return [fact for fact in facts if _evidence_grounded(fact, context)]


def _evidence_grounded(fact: KgcFact, context: str) -> bool:
    evidence = fact.evidence or ""
    if not evidence:
        return False
    return normalize(evidence) in normalize(context) or evidence in context


def _diagnosis_fact(subject: str, context: str) -> KgcFact | None:
    patterns = [
        re.compile(
            rf"{re.escape(subject)}\s+has\s+([^.]+?)(?:\.|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:has|diagnosed with|diagnosis of)\s+([^.]+?)(?:\.|$)",
            re.IGNORECASE,
        ),
    ]
    for pattern in patterns:
        match = pattern.search(context)
        if not match:
            continue
        diagnosis = match.group(1).strip().rstrip(".")
        if not diagnosis:
            continue
        # Prefer diabetes/condition phrases; skip unrelated "has" clauses.
        if not any(
            marker in diagnosis.lower()
            for marker in ("diabetes", "mellitus", "disease", "disorder", "condition")
        ):
            # Still accept short clinical diagnosis phrases.
            if len(diagnosis.split()) > 8:
                continue
        evidence = match.group(0).strip().rstrip(".")
        return KgcFact(
            subject=subject,
            relation=INTENT_CANONICAL_RELATIONS["diagnosis"],
            object=diagnosis,
            evidence=evidence,
        )
    return None


def _a1c_fact(subject: str, context: str) -> KgcFact | None:
    match = re.search(
        r"((?:latest\s+)?(?:hemoglobin\s+)?A1C(?:\s+is|\s+of|:)?\s*\d+(?:\.\d+)?\s*%)",
        context,
        flags=re.IGNORECASE,
    )
    if not match:
        value = extract_a1c(context)
        if not value:
            return None
        # Find a short evidence span containing the value.
        idx = context.lower().find(value.lower().rstrip("%"))
        evidence = context[max(0, idx - 20) : idx + 30].strip() if idx >= 0 else value
        return KgcFact(
            subject=subject,
            relation=INTENT_CANONICAL_RELATIONS["lab_measurement"],
            object=value,
            evidence=evidence,
        )
    evidence = match.group(1).strip()
    value = extract_a1c(evidence)
    if not value:
        return None
    return KgcFact(
        subject=subject,
        relation=INTENT_CANONICAL_RELATIONS["lab_measurement"],
        object=value,
        evidence=evidence,
    )


def _stage_fact(subject: str, context: str) -> KgcFact | None:
    match = re.search(
        r"((?:chronic kidney disease|CKD)\s+stage\s*[0-9][a-z]?)",
        context,
        flags=re.IGNORECASE,
    )
    stage = extract_ckd_stage(match.group(1) if match else context)
    if not stage:
        return None
    evidence = match.group(1) if match else stage
    return KgcFact(
        subject=subject,
        relation=INTENT_CANONICAL_RELATIONS["disease_stage"],
        object=stage,
        evidence=evidence,
    )


def _egfr_fact(subject: str, context: str) -> KgcFact | None:
    match = re.search(
        r"((?:current\s+)?eGFR\s*(?:of\s*)?\d+(?:\.\d+)?\s*mL/?min(?:/1\.73\s*m[²2])?)",
        context,
        flags=re.IGNORECASE,
    )
    value = extract_egfr(match.group(1) if match else context)
    if not value:
        return None
    evidence = match.group(1) if match else value
    return KgcFact(
        subject=subject,
        relation=INTENT_CANONICAL_RELATIONS["renal_measurement"],
        object=value,
        evidence=evidence,
    )


def _discontinued_facts(subject: str, context: str, intent: str) -> list[KgcFact]:
    facts: list[KgcFact] = []
    match = re.search(
        r"([A-Za-z][A-Za-z0-9\-]*)\s+was discontinued(?:\s+after\s+(.+?))?(?:\.|$)",
        context,
        flags=re.IGNORECASE,
    )
    if not match:
        return facts
    med = match.group(1)
    evidence = match.group(0).strip().rstrip(".")
    facts.append(
        KgcFact(
            subject=subject,
            relation=INTENT_CANONICAL_RELATIONS["medication_discontinued"],
            object=med,
            evidence=evidence,
        )
    )
    if intent == "discontinued_medication_with_reason" and match.group(2):
        reason = match.group(2).strip()
        reason = re.sub(
            r"^(?:repeated trials caused|causing)\s+",
            "",
            reason,
            flags=re.IGNORECASE,
        )
        facts.append(
            KgcFact(
                subject=subject,
                relation=INTENT_CANONICAL_RELATIONS["discontinuation_reason"],
                object=reason,
                evidence=evidence,
            )
        )
    return facts


def _active_med_facts(subject: str, context: str, intent: str) -> list[KgcFact]:
    facts: list[KgcFact] = []
    match = re.search(
        r"([A-Za-z][A-Za-z0-9\-]*)\s+(\d+(?:\.\d+)?\s*mg(?:\s*daily)?)\s+"
        r"(?:remains\s+)?active",
        context,
        flags=re.IGNORECASE,
    )
    if not match:
        # Fallback: active + tolerated phrasing
        match = re.search(
            r"([A-Za-z][A-Za-z0-9\-]*)\s+(\d+(?:\.\d+)?\s*mg(?:\s*daily)?).{0,40}"
            r"(?:active|tolerated)",
            context,
            flags=re.IGNORECASE,
        )
    if not match:
        return facts
    med = match.group(1)
    dose = extract_dose(match.group(2)) or match.group(2)
    evidence = match.group(0).strip()
    facts.append(
        KgcFact(
            subject=subject,
            relation=INTENT_CANONICAL_RELATIONS["active_medication"],
            object=med,
            evidence=evidence,
        )
    )
    if intent == "active_medication_with_dose":
        facts.append(
            KgcFact(
                subject=subject,
                relation=INTENT_CANONICAL_RELATIONS["medication_dose"],
                object=dose,
                evidence=evidence,
            )
        )
    return facts


def _discussed_fact(subject: str, context: str) -> KgcFact | None:
    match = re.search(
        r"([A-Za-z][A-Za-z0-9\-]*)\s+was discussed.{0,80}not been started",
        context,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"([A-Za-z][A-Za-z0-9\-]*)\s+was discussed as a future treatment option",
            context,
            flags=re.IGNORECASE,
        )
    if not match:
        return None
    return KgcFact(
        subject=subject,
        relation=INTENT_CANONICAL_RELATIONS["discussed_not_started"],
        object=match.group(1),
        evidence=match.group(0).strip(),
    )


def _allergy_facts(subject: str, context: str, intent: str) -> list[KgcFact]:
    facts: list[KgcFact] = []
    match = re.search(
        r"(?:allergy list records|allergic to)\s+([A-Za-z][A-Za-z0-9\-]*)"
        r"(?:\s+causing\s+([^.]+))?",
        context,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"records\s+([A-Za-z][A-Za-z0-9\-]*)\s+causing\s+([^.]+)",
            context,
            flags=re.IGNORECASE,
        )
    if not match:
        return facts
    allergen = match.group(1)
    evidence = match.group(0).strip().rstrip(".")
    facts.append(
        KgcFact(
            subject=subject,
            relation=INTENT_CANONICAL_RELATIONS["allergy"],
            object=allergen,
            evidence=evidence,
        )
    )
    if intent == "allergy_with_reaction" and match.lastindex and match.lastindex >= 2 and match.group(2):
        facts.append(
            KgcFact(
                subject=subject,
                relation=INTENT_CANONICAL_RELATIONS["allergic_reaction"],
                object=match.group(2).strip().rstrip("."),
                evidence=evidence,
            )
        )
    return facts


def _mission_date_fact(subject: str, context: str) -> KgcFact | None:
    # Reusable interval pattern — not Apollo-specific values.
    match = re.search(
        r"\(([A-Za-z]+\s+\d{1,2}\s*[-–—]\s*\d{1,2},\s*\d{4})\)",
        context,
    )
    if not match:
        match = re.search(
            r"((?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December)\s+\d{1,2}\s*[-–—]\s*\d{1,2},\s*\d{4})",
            context,
            flags=re.IGNORECASE,
        )
    if not match:
        return None
    value = match.group(1).strip()
    return KgcFact(
        subject=subject if subject != "Patient" else subject,
        relation="occurred_between",
        object=value,
        evidence=match.group(0).strip(),
    )
