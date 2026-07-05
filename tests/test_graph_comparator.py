"""Unit tests for KGc graph comparator."""

from src.models import KgcClaimLabel, KgcFact, Triple
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_matching import normalize, normalize_relation

HYUNDAI = "2018 Hyundai Sonata SE"


def test_exact_kgc_fact_is_labeled_supported():
    """Exact subject-relation-object match against KGc should be SUPPORTED."""
    kgc_facts = [
        KgcFact(
            subject=HYUNDAI,
            relation="has_engine",
            object="2.4L engine",
            evidence="The 2018 Hyundai Sonata SE has a 2.4L engine",
        )
    ]
    claim = Triple(
        subject=HYUNDAI,
        relation="has_engine",
        object="2.4L engine",
    )

    results = GraphComparator().compare_claims([claim], kgc_facts)

    assert len(results) == 1
    assert results[0].label == KgcClaimLabel.SUPPORTED, (
        "Expected exact KGc fact match to be SUPPORTED"
    )
    assert results[0].reason == "Claim matches a KGc fact."


def test_relation_wording_is_normalized_before_comparison():
    """Surface relation variants like was_assembled_in should match assembled_in in KGc."""
    assert normalize_relation("was_assembled_in") == "assembled_in", (
        "Auxiliary prefix should be stripped before comparison"
    )
    assert normalize_relation("has_engine") == "has_engine", (
        "Meaningful prefixes like has_ must not be removed"
    )

    kgc_facts = [
        KgcFact(
            subject=HYUNDAI,
            relation="assembled_in",
            object="Alabama",
            evidence="was assembled in Alabama",
        )
    ]
    claim = Triple(
        subject=HYUNDAI,
        relation="was_assembled_in",
        object="Alabama",
    )

    results = GraphComparator().compare_claims([claim], kgc_facts)

    assert results[0].label == KgcClaimLabel.SUPPORTED, (
        "Expected normalized relation wording to match KGc fact as SUPPORTED"
    )
    assert "normalization" in results[0].reason.lower(), (
        "Reason should explain that relation normalization enabled the match"
    )
    assert "Alabama" in results[0].evidence, (
        "Matched KGc fact should appear in evidence"
    )


def test_conflicting_object_is_labeled_contradicted():
    """Same subject-relation with a different object should be CONTRADICTED."""
    kgc_facts = [
        KgcFact(
            subject=HYUNDAI,
            relation="assembled_in",
            object="Alabama",
        )
    ]
    claim = Triple(
        subject=HYUNDAI,
        relation="assembled_in",
        object="Korea",
    )

    results = GraphComparator().compare_claims([claim], kgc_facts)

    assert results[0].label == KgcClaimLabel.CONTRADICTED, (
        "Expected conflicting object to be CONTRADICTED"
    )
    assert results[0].conflicting_object == "Alabama", (
        "Conflicting KGc object should be recorded"
    )


def test_missing_kgc_support_is_labeled_no_evidence():
    """Claims with no KGc subject-relation support should be NO_EVIDENCE."""
    kgc_facts = [
        KgcFact(
            subject=HYUNDAI,
            relation="assembled_in",
            object="Alabama",
        )
    ]
    claim = Triple(
        subject=HYUNDAI,
        relation="has_turbo",
        object="true",
    )

    results = GraphComparator().compare_claims([claim], kgc_facts)

    assert results[0].label == KgcClaimLabel.NO_EVIDENCE, (
        "Expected claim with no KGc support to be NO_EVIDENCE"
    )
