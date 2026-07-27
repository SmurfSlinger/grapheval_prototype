"""Directional integrity for extracted KG claims.

Canonical passive relations encode a fixed argument order. Active prose such as
"X studies Y" must map to ``Y — is_studied_by → X``, not the reverse.

This module never marks a claim SUPPORTED merely because the reverse KG edge
exists. It either corrects direction from answer/source grammar, or leaves the
claim unchanged and records a directional anomaly for the trace.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from src.models import KgcFact, Triple
from src.pipeline.debug_log import log_debug_event
from src.pipeline.kgc_matching import normalize, normalize_relation

# Active surface verb → canonical passive relation.
# Direction: "{agent} {verb} {patient}" ⇒ patient — passive → agent
ACTIVE_TO_PASSIVE: dict[str, str] = {
    "studies": "is_studied_by",
    "study": "is_studied_by",
    "studied": "is_studied_by",
    "employs": "is_employed_by",
    "employ": "is_employed_by",
    "employed": "is_employed_by",
    "contains": "is_located_in",
    "contain": "is_located_in",
    "containing": "is_located_in",
    "founded": "is_founded_by",
    "founds": "is_founded_by",
    "administers": "is_administered_by",
    "administer": "is_administered_by",
    "administered": "is_administered_by",
    "produces": "produced_by",
    "produce": "produced_by",
    "produced": "produced_by",
    "builds": "built_by",
    "build": "built_by",
    "built": "built_by",
    "leads": "led_by",
    "lead": "led_by",
    "led": "led_by",
    "crews": "crewed_by",
    "crew": "crewed_by",
    "crewed": "crewed_by",
}

PASSIVE_CANONICAL_RELATIONS = frozenset(
    {
        "is_studied_by",
        "studied_by",
        "is_employed_by",
        "employed_by",
        "is_located_in",
        "located_in",
        "situated_in",
        "is_founded_by",
        "founded_by",
        "is_administered_by",
        "administered_by",
        "produced_by",
        "built_by",
        "manufactured_by",
        "made_by",
        "led_by",
        "crewed_by",
        "launched_by",
        "launched_from",
    }
)

_PASSIVE_EQUIVALENTS: dict[str, frozenset[str]] = {
    "is_studied_by": frozenset({"is_studied_by", "studied_by"}),
    "is_employed_by": frozenset({"is_employed_by", "employed_by"}),
    "is_located_in": frozenset({"is_located_in", "located_in", "situated_in"}),
    "is_founded_by": frozenset({"is_founded_by", "founded_by"}),
    "is_administered_by": frozenset({"is_administered_by", "administered_by"}),
    "produced_by": frozenset({"produced_by", "built_by", "manufactured_by", "made_by"}),
    "built_by": frozenset({"built_by", "produced_by", "manufactured_by", "made_by"}),
    "led_by": frozenset({"led_by", "headed_by", "governed_by", "commanded_by"}),
    "crewed_by": frozenset({"crewed_by", "was_crewed_by"}),
}


@dataclass
class DirectionalAnomaly:
    reason: str
    claim_subject: str
    claim_relation: str
    claim_object: str
    reverse_fact_subject: str | None = None
    reverse_fact_relation: str | None = None
    reverse_fact_object: str | None = None
    corrected: bool = False
    correction_subject: str | None = None
    correction_object: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_directional_passive_relation(relation: str) -> bool:
    rel = normalize_relation(relation)
    if rel in PASSIVE_CANONICAL_RELATIONS:
        return True
    return rel.endswith("_by") or rel.startswith("is_")


def _entity_in_text(entity: str, text: str) -> bool:
    ent = normalize(entity)
    if not ent or not text:
        return False
    return ent in normalize(text)


def _relations_equivalent_passive(left: str, right: str) -> bool:
    left_n = normalize_relation(left)
    right_n = normalize_relation(right)
    if left_n == right_n:
        return True
    for group in _PASSIVE_EQUIVALENTS.values():
        if left_n in group and right_n in group:
            return True
    return False


def find_reverse_entity_pair_fact(
    claim: Triple,
    kgc_facts: list[KgcFact],
) -> KgcFact | None:
    """Return a trusted FACT with the same relation and swapped endpoints, if any."""
    for fact in kgc_facts:
        if not _relations_equivalent_passive(claim.relation, fact.relation):
            continue
        if (
            normalize(fact.subject) == normalize(claim.object)
            and normalize(fact.object) == normalize(claim.subject)
        ):
            return fact
    return None


def _active_grammar_correction(claim: Triple, source: str) -> Triple | None:
    """Correct inverted passive claims using active grammar in the source sentence."""
    if not is_directional_passive_relation(claim.relation):
        return None
    text = source.strip()
    if not text:
        return None

    claim_rel = normalize_relation(claim.relation)
    agent = claim.subject
    patient = claim.object
    for verb, passive in ACTIVE_TO_PASSIVE.items():
        if not _relations_equivalent_passive(claim_rel, passive):
            continue
        # "{agent} {verb} {patient}" with passive relation on agent→patient is inverted.
        active = re.compile(
            rf"\b{re.escape(agent)}\b\s+{verb}\b[\s\S]*?\b{re.escape(patient)}\b",
            re.IGNORECASE,
        )
        if active.search(text):
            return Triple(
                subject=patient,
                relation=claim.relation
                if claim_rel == normalize_relation(passive)
                else passive,
                object=agent,
                source_sentence=claim.source_sentence,
            )
    return None


def enforce_claim_direction_integrity(
    claims: list[Triple],
    kgc_facts: list[KgcFact],
    *,
    answer: str = "",
) -> tuple[list[Triple], list[DirectionalAnomaly]]:
    """Detect/correct directional inversions without KG-only auto-support.

    When the exact forward claim has no KG match, the reverse entity pair exists,
    both entities appear in the source sentence, and the relation is directional:
    attempt grammar-based correction. Otherwise leave the claim unaligned and
    record a directional anomaly.
    """
    if not claims:
        return claims, []

    corrected: list[Triple] = []
    anomalies: list[DirectionalAnomaly] = []

    fact_keys = {
        (
            normalize(fact.subject),
            normalize_relation(fact.relation),
            normalize(fact.object),
        )
        for fact in kgc_facts
    }

    for claim in claims:
        forward_key = (
            normalize(claim.subject),
            normalize_relation(claim.relation),
            normalize(claim.object),
        )
        if forward_key in fact_keys:
            corrected.append(claim)
            continue

        reverse = find_reverse_entity_pair_fact(claim, kgc_facts)
        if reverse is None or not is_directional_passive_relation(claim.relation):
            corrected.append(claim)
            continue

        source = claim.source_sentence or answer
        entities_in_source = _entity_in_text(claim.subject, source) and _entity_in_text(
            claim.object, source
        )
        if not entities_in_source:
            anomaly = DirectionalAnomaly(
                reason="reverse_pair_without_source_support",
                claim_subject=claim.subject,
                claim_relation=claim.relation,
                claim_object=claim.object,
                reverse_fact_subject=reverse.subject,
                reverse_fact_relation=reverse.relation,
                reverse_fact_object=reverse.object,
                corrected=False,
            )
            anomalies.append(anomaly)
            log_debug_event("claim_direction", anomaly.reason, anomaly.to_dict())
            corrected.append(claim)
            continue

        grammar_fix = _active_grammar_correction(claim, source)
        if grammar_fix is not None and (
            normalize(grammar_fix.subject) != normalize(claim.subject)
            or normalize(grammar_fix.object) != normalize(claim.object)
        ):
            anomaly = DirectionalAnomaly(
                reason="directional_inversion_corrected_from_source_grammar",
                claim_subject=claim.subject,
                claim_relation=claim.relation,
                claim_object=claim.object,
                reverse_fact_subject=reverse.subject,
                reverse_fact_relation=reverse.relation,
                reverse_fact_object=reverse.object,
                corrected=True,
                correction_subject=grammar_fix.subject,
                correction_object=grammar_fix.object,
            )
            anomalies.append(anomaly)
            log_debug_event("claim_direction", anomaly.reason, anomaly.to_dict())
            corrected.append(grammar_fix)
            continue

        anomaly = DirectionalAnomaly(
            reason="directional_inversion_unresolved",
            claim_subject=claim.subject,
            claim_relation=claim.relation,
            claim_object=claim.object,
            reverse_fact_subject=reverse.subject,
            reverse_fact_relation=reverse.relation,
            reverse_fact_object=reverse.object,
            corrected=False,
        )
        anomalies.append(anomaly)
        log_debug_event("claim_direction", anomaly.reason, anomaly.to_dict())
        # Leave unaligned — do not flip solely because the reverse FACT exists.
        corrected.append(claim)

    return corrected, anomalies
