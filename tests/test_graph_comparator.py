"""Unit tests for KGc graph comparator."""

from __future__ import annotations

import pytest

from src.models import KgcClaimLabel, KgcFact, Triple
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_matching import normalize, normalize_relation
from src.pipeline.question_target import derive_question_target
from src.pipeline.target_frame_normalizer import relations_share_target_family

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


def _compare(claim: Triple, kgc: list[KgcFact], *, question: str | None = None):
    comparator = GraphComparator()
    if question:
        target = derive_question_target(question, kgc)
        return comparator.compare_claims(
            [claim], kgc, question_target=target, question=question
        )[0]
    return comparator.compare_claims([claim], kgc)[0]


@pytest.mark.parametrize(
    ("case_id", "kgc", "claim", "question", "expected"),
    [
        (
            "exact_match",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("Host C", "located_in", "Rack R7"),
            None,
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "relation_normalization",
            [KgcFact(HYUNDAI, "assembled_in", "Alabama")],
            Triple(HYUNDAI, "was_assembled_in", "Alabama"),
            None,
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "subject_normalization_whitespace",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("  Host   C  ", "located_in", "Rack R7"),
            None,
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "alias_mission_to_apollo",
            [KgcFact("Apollo 11", "launched_from", "Kennedy Space Center")],
            Triple("the mission", "launched_from", "Kennedy Space Center"),
            "Where was Apollo 11 launched from?",
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "correct_object",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("Host C", "located_in", "Rack R7"),
            None,
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "conflicting_object",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("Host C", "located_in", "Rack R99"),
            None,
            KgcClaimLabel.CONTRADICTED,
        ),
        (
            "no_matching_fact",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("Host C", "powered_by", "diesel"),
            None,
            KgcClaimLabel.NO_EVIDENCE,
        ),
        (
            "negative_polarity",
            [KgcFact("Drone Alpha-7", "does_not_carry", "weapons")],
            Triple("Drone Alpha-7", "carries", "weapons"),
            None,
            KgcClaimLabel.CONTRADICTED,
        ),
        (
            "similarly_named_distinct_entities",
            [
                KgcFact("Apollo 11", "launched_by", "Saturn V"),
                KgcFact("Apollo 12", "launched_by", "Saturn V"),
            ],
            Triple("Apollo 12", "launched_by", "Saturn IB"),
            None,
            KgcClaimLabel.CONTRADICTED,
        ),
        (
            "duplicate_names_different_branches",
            [
                KgcFact("Service A", "depends_on", "Database B"),
                KgcFact("Service Z", "depends_on", "Database B-alt"),
            ],
            Triple("Service Z", "depends_on", "Database B"),
            None,
            KgcClaimLabel.CONTRADICTED,
        ),
        (
            "multiple_object_matches_no_false_support",
            [
                KgcFact("Host C", "located_in", "Rack R7"),
                KgcFact("Spare Host", "located_in", "Rack R7"),
            ],
            Triple("Unknown Host", "located_in", "Rack R8"),
            None,
            KgcClaimLabel.NO_EVIDENCE,
        ),
        (
            "dates_supported",
            [KgcFact("Apollo 11", "occurred_between", "July 16-24, 1969")],
            Triple("Apollo 11", "occurred_during", "July 16-24, 1969"),
            "When was the Apollo 11 mission?",
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "dates_conflicted",
            [KgcFact("Apollo 11", "occurred_between", "July 16-24, 1969")],
            Triple("Apollo 11", "occurred_during", "july 16-august 5, 1985"),
            "When was the Apollo 11 mission?",
            KgcClaimLabel.CONTRADICTED,
        ),
        (
            "numerical_values",
            [KgcFact("Apollo 11", "lunar_material_collected", "47.5 pounds")],
            Triple("Apollo 11", "collected", "47.5 pounds"),
            "How much lunar material did Apollo 11 collect?",
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "apollo_crew",
            [
                KgcFact(
                    "Apollo 11",
                    "crewed_by",
                    "Neil Armstrong, Buzz Aldrin, Michael Collins",
                )
            ],
            Triple(
                "Apollo 11",
                "crewed_by",
                "Neil Armstrong, Buzz Aldrin, Michael Collins",
            ),
            "Who were the astronauts on the Apollo 11 mission?",
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "apollo_vehicle",
            [KgcFact("Apollo 11", "launched_by", "Saturn V")],
            Triple("Apollo 11", "was_launched_by", "Saturn V"),
            "What rocket launched Apollo 11?",
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "apollo_location",
            [KgcFact("Apollo 11", "launched_from", "Kennedy Space Center")],
            Triple("Apollo 11", "launched_from", "Kennedy Space Center"),
            "Where was Apollo 11 launched from?",
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "arbitrary_relation_outside_families",
            [KgcFact("Widget X", "firmware_version", "3.2.1")],
            Triple("Widget X", "firmware_version", "3.2.1"),
            None,
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "arbitrary_relation_conflict",
            [KgcFact("Widget X", "firmware_version", "3.2.1")],
            Triple("Widget X", "firmware_version", "9.9.9"),
            None,
            KgcClaimLabel.CONTRADICTED,
        ),
    ],
)
def test_graph_comparator_table_driven(
    case_id: str,
    kgc: list[KgcFact],
    claim: Triple,
    question: str | None,
    expected: KgcClaimLabel,
):
    result = _compare(claim, kgc, question=question)
    assert result.label == expected, f"{case_id}: {result.reason}"


def test_answer_side_object_leakage_prevention():
    """Wrong answer object must stay contradicted; KGc object must not overwrite it."""
    kgc = [KgcFact("Host C", "located_in", "Rack R7")]
    claim = Triple("Host C", "located_in", "Rack R99")
    result = GraphComparator().compare_claims([claim], kgc)[0]
    assert result.label == KgcClaimLabel.CONTRADICTED
    assert result.triple.object == "Rack R99"
    assert result.conflicting_object == "Rack R7"


def test_ambiguous_alignment_does_not_force_support_via_shared_object():
    kgc = [
        KgcFact("Host C", "located_in", "Rack R7"),
        KgcFact("Spare Host", "stored_in", "Rack R7"),
    ]
    claim = Triple("Mystery Host", "located_in", "Rack R7")
    result = GraphComparator().compare_claims([claim], kgc)[0]
    # Without subject match this is contradicted against Host C's located_in fact
    # only if subject+relation collide; Mystery Host has no SR key → NO_EVIDENCE.
    assert result.label == KgcClaimLabel.NO_EVIDENCE


def test_target_relation_family_matching_and_exclusions():
    assert relations_share_target_family(
        "crewed_by", "was_crewed_by", "crew_members"
    )
    assert not relations_share_target_family(
        "crewed_by", "launched_by", "crew_members"
    )
    assert relations_share_target_family(
        "active_medication", "currently_taking", "active_medication"
    )
    # Exclusions: active-medication intent must not treat discontinued as same family.
    assert not relations_share_target_family(
        "active_medication", "discontinued_medication", "active_medication"
    )

    kgc = [KgcFact("Patient Case D-314", "active_medication", "empagliflozin")]
    claim = Triple("Patient Case D-314", "currently_taking", "empagliflozin")
    question = "Which diabetes medication is currently active and tolerated?"
    result = _compare(claim, kgc, question=question)
    assert result.label == KgcClaimLabel.SUPPORTED



def test_normalize_helpers_used_by_comparator():
    assert normalize("  Rack   R7 ") == "rack r7"
    assert normalize_relation("was_located_in") == "located_in"


def test_table_driven_comparator_core_cases():
    cases = [
        (
            "exact",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("Host C", "located_in", "Rack R7"),
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "relation_norm",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("Host C", "is_located_in", "Rack R7"),
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "conflict",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("Host C", "located_in", "Rack R9"),
            KgcClaimLabel.CONTRADICTED,
        ),
        (
            "no_evidence",
            [KgcFact("Host C", "located_in", "Rack R7")],
            Triple("Host C", "painted", "blue"),
            KgcClaimLabel.NO_EVIDENCE,
        ),
        (
            "similar_names_distinct",
            [
                KgcFact("Host C", "located_in", "Rack R7"),
                KgcFact("Host C2", "located_in", "Rack R8"),
            ],
            Triple("Host C2", "located_in", "Rack R8"),
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "general_relation",
            [KgcFact("Widget X", "manufactured_by", "Acme Corp")],
            Triple("Widget X", "manufactured_by", "Acme Corp"),
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "general_conflict",
            [KgcFact("Widget X", "manufactured_by", "Acme Corp")],
            Triple("Widget X", "manufactured_by", "Globex"),
            KgcClaimLabel.CONTRADICTED,
        ),
        (
            "apollo_launch_vehicle_style",
            [KgcFact("Apollo 11", "launched_by", "Saturn V")],
            Triple("Apollo 11", "launched_by", "Saturn V"),
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "numeric_units",
            [KgcFact("Tank", "holds", "50 gallons")],
            Triple("Tank", "holds", "50 gallons"),
            KgcClaimLabel.SUPPORTED,
        ),
        (
            "date_value",
            [KgcFact("Apollo 11", "launched_on", "July 16, 1969")],
            Triple("Apollo 11", "launched_on", "July 16, 1969"),
            KgcClaimLabel.SUPPORTED,
        ),
    ]
    comparator = GraphComparator()
    for name, facts, claim, expected in cases:
        result = comparator.compare_claims([claim], facts)[0]
        assert result.label == expected, (
            f"{name}: {result.label} != {expected} ({result.reason})"
        )


def test_answer_object_not_supported_just_because_benchmark_knows_answer():
    facts = [KgcFact("Host C", "located_in", "Rack R7")]
    claim = Triple("Host C", "located_in", "Rack R9")
    result = GraphComparator().compare_claims([claim], facts)[0]
    assert result.label == KgcClaimLabel.CONTRADICTED
