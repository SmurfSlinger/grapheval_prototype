"""Tests for KGc schema alignment of extracted claims."""

from src.models import KgcClaimLabel, KgcFact, Triple
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema

DRONE = "Drone Alpha-7"

DRONE_KGC = [
    KgcFact(DRONE, "has_maximum_flight_time", "42 minutes"),
    KgcFact(DRONE, "approved_for", "daylight reconnaissance"),
    KgcFact(DRONE, "does_not_carry", "weapons"),
]

MISALIGNED_DRONE_CLAIMS = [
    Triple("Flight time", "has_value", "42 minutes"),
    Triple("Reconnaissance approval", "approved_for", "daylight reconnaissance"),
    Triple("Weapons status", "does_not_carry", "weapons"),
]


def test_drone_misaligned_claims_align_to_kgc_schema():
    aligned, _ = align_claims_to_kgc_schema(MISALIGNED_DRONE_CLAIMS, DRONE_KGC)

    assert len(aligned) == 3
    assert aligned[0].subject == DRONE
    assert aligned[0].relation == "has_maximum_flight_time"
    assert aligned[0].object == "42 minutes"
    assert aligned[1].relation == "approved_for"
    assert aligned[2].relation == "does_not_carry"
    assert all(t.source_sentence and "Aligned from:" in t.source_sentence for t in aligned)


def test_drone_aligned_claims_evaluate_as_supported():
    aligned, _ = align_claims_to_kgc_schema(MISALIGNED_DRONE_CLAIMS, DRONE_KGC)
    results = GraphComparator().compare_claims(aligned, DRONE_KGC)

    assert len(results) == 3
    assert all(r.label == KgcClaimLabel.SUPPORTED for r in results)
    assert results[0].label.value == "SUPPORTED"
    assert "aligned" in results[0].reason.lower() or "matches" in results[0].reason.lower()


def test_genuine_no_evidence_claim_not_aligned():
    claims = MISALIGNED_DRONE_CLAIMS + [
        Triple(DRONE, "supports_autonomous_night_operations", "true"),
    ]
    aligned, _ = align_claims_to_kgc_schema(claims, DRONE_KGC)
    results = GraphComparator().compare_claims(aligned, DRONE_KGC)

    assert results[-1].label == KgcClaimLabel.NO_EVIDENCE
    assert sum(1 for r in results if r.label == KgcClaimLabel.SUPPORTED) == 3


def test_positive_carry_claim_does_not_align_via_unique_object():
    claims = [Triple("Weapons status", "carries", "weapons")]
    aligned, _ = align_claims_to_kgc_schema(claims, DRONE_KGC)

    assert aligned[0].relation == "carries"
    assert aligned[0].subject == "Weapons status"


APOLLO_KGC = [
    KgcFact("Apollo 11", "launched_by", "Saturn V"),
    KgcFact("Apollo 11", "launched_from", "Launch Complex 39A"),
    KgcFact("Apollo 11", "launched_at", "Kennedy Space Center"),
    KgcFact("Saturn V S-IC stage", "powered_by", "five F-1 engines"),
    KgcFact("Apollo 11", "achieved", "first crewed Moon landing"),
]


def test_apollo_flawed_answer_claims_include_launch_site():
    claims = [
        Triple("Apollo 11", "was_launched_by", "a Saturn IB rocket"),
        Triple("Apollo 11", "launched_from", "Cape Canaveral"),
        Triple("Apollo 11 first stage", "used", "five J-2 engines"),
        Triple("Apollo 11", "achieved", "first crewed Moon landing"),
    ]
    aligned, _ = align_claims_to_kgc_schema(claims, APOLLO_KGC)

    assert len(aligned) == 4
    assert aligned[0].relation == "launched_by"
    assert aligned[0].object == "a Saturn IB rocket"
    assert aligned[1].relation == "launched_from"
    assert aligned[1].object == "Cape Canaveral"

    results = GraphComparator().compare_claims(aligned, APOLLO_KGC)
    labels = {r.triple.relation: r.label for r in results}
    assert labels["launched_by"] == KgcClaimLabel.CONTRADICTED
    assert labels["launched_from"] == KgcClaimLabel.CONTRADICTED
    assert labels["powered_by"] == KgcClaimLabel.CONTRADICTED
    assert labels["achieved"] == KgcClaimLabel.SUPPORTED


def test_apollo_first_stage_used_claim_aligns_and_contradicts():
    claim = Triple("Apollo 11 first stage", "used", "five J-2 engines")
    aligned, _ = align_claims_to_kgc_schema([claim], APOLLO_KGC)

    assert aligned[0].subject == "Saturn V S-IC stage"
    assert aligned[0].relation == "powered_by"
    assert aligned[0].object == "five J-2 engines"

    results = GraphComparator().compare_claims(aligned, APOLLO_KGC)
    assert results[0].label == KgcClaimLabel.CONTRADICTED
    assert results[0].conflicting_fact is not None
    assert "F-1" in results[0].conflicting_fact.object
