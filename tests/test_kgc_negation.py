"""Tests for negation/polarity preservation in KGc matching."""

from src.models import KgcClaimLabel, KgcFact, Triple
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema

DRONE = "Drone Alpha-7"

DRONE_KGC = [
    KgcFact(DRONE, "does_not_carry", "weapons", evidence="It does not carry weapons"),
]


def test_negated_kgc_fact_supported_when_claim_matches():
    claim = Triple(DRONE, "does_not_carry", "weapons")
    results = GraphComparator().compare_claims([claim], DRONE_KGC)

    assert results[0].label == KgcClaimLabel.SUPPORTED


def test_positive_carry_claim_not_supported_against_negated_kgc_fact():
    """Opposite polarity must not be treated as SUPPORTED."""
    claim = Triple(DRONE, "carries", "weapons")
    results = GraphComparator().compare_claims([claim], DRONE_KGC)

    assert results[0].label != KgcClaimLabel.SUPPORTED
    assert results[0].label in (KgcClaimLabel.CONTRADICTED, KgcClaimLabel.NO_EVIDENCE)


def test_polarity_conflict_is_contradicted():
    claim = Triple(DRONE, "carries", "weapons")
    results = GraphComparator().compare_claims([claim], DRONE_KGC)

    assert results[0].label == KgcClaimLabel.CONTRADICTED
    assert "polarity" in results[0].reason.lower() or "conflict" in results[0].reason.lower()


def test_aligner_does_not_flip_positive_carry_to_does_not_carry():
    claims = [Triple("Weapons status", "carries", "weapons")]
    aligned, _ = align_claims_to_kgc_schema(claims, DRONE_KGC)

    assert aligned[0].relation == "carries"
    results = GraphComparator().compare_claims(aligned, DRONE_KGC)
    assert results[0].label != KgcClaimLabel.SUPPORTED
