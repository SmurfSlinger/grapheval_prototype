"""Regression: nested-question intent must follow the grammatical target."""

from __future__ import annotations

from src.models import (
    KgcClaimLabel,
    KgcEvaluationResult,
    KgcFact,
    Triple,
)
from src.pipeline.backtracking_feedback_builder import BacktrackingFeedbackBuilder
from src.pipeline.claim_grounding import ground_claim_objects_in_answer
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.question_target import (
    condition_claims_to_question,
    derive_question_target,
    evaluate_target_satisfaction,
    parse_interrogative_frame,
)


APOLLO_FACTS = [
    KgcFact(
        "Apollo 11",
        "crewed_by",
        "Neil Armstrong",
        evidence="Apollo 11 was crewed by Neil Armstrong.",
    ),
    KgcFact(
        "Neil Armstrong",
        "born_in",
        "Wapakoneta",
        evidence="Neil Armstrong was born in Wapakoneta.",
    ),
]


def _trace_stages(question: str, answer: str, facts: list[KgcFact]):
    target = derive_question_target(question, facts)
    raw = Triple("Neil Armstrong", "born_in", answer, source_sentence=answer)
    conditioned = condition_claims_to_question([raw], question, answer, target, facts)
    grounded, _ = ground_claim_objects_in_answer(conditioned, answer)
    aligned, _ = align_claims_to_kgc_schema(grounded, facts, question_target=target)
    evaluations = GraphComparator().compare_claims(
        aligned,
        facts,
        question_target=target,
        question=question,
    )
    satisfaction = evaluate_target_satisfaction(evaluations, target)
    feedback = BacktrackingFeedbackBuilder().build(evaluations)
    return {
        "target": target,
        "raw": raw,
        "conditioned": conditioned,
        "grounded": grounded,
        "aligned": aligned,
        "evaluations": evaluations,
        "satisfaction": satisfaction,
        "feedback": feedback,
    }


def test_nested_birthplace_question_is_not_hijacked_by_crew_qualifier():
    question = "In which town was the Apollo 11 crew member Neil Armstrong born?"
    stages = _trace_stages(question, "Wapakoneta", APOLLO_FACTS)

    assert stages["target"].intent == "birthplace"
    assert stages["target"].canonical_relation == "born_in"
    assert stages["target"].primary_subject == "Neil Armstrong"

    assert [(c.subject, c.relation, c.object) for c in stages["conditioned"]] == [
        ("Neil Armstrong", "born_in", "Wapakoneta")
    ]
    assert [(c.subject, c.relation, c.object) for c in stages["aligned"]] == [
        ("Neil Armstrong", "born_in", "Wapakoneta")
    ]
    assert stages["evaluations"][0].label == KgcClaimLabel.SUPPORTED
    assert stages["satisfaction"].satisfied is True
    assert not any(
        item.label == KgcClaimLabel.CONTRADICTED for item in stages["feedback"]
    )


def test_true_crew_question_still_selects_crew_members():
    target = derive_question_target(
        "Which crew member flew on Apollo 11?",
        APOLLO_FACTS,
    )
    assert target.intent == "crew_members"
    assert "crewed_by" in target.expected_relations


def test_nested_containment_question_selects_location_not_birthplace():
    target = derive_question_target(
        "Which state contains the town where Neil Armstrong was born?",
        APOLLO_FACTS
        + [KgcFact("Wapakoneta", "located_in", "Ohio")],
    )
    assert target.intent == "location_containment"
    assert target.canonical_relation == "located_in"


def test_manufacturer_question_not_hijacked_by_launch_qualifier():
    target = derive_question_target(
        "Which company built the first stage of the rocket that launched Apollo 11?",
        [
            KgcFact("Apollo 11", "launched_by", "Saturn V"),
            KgcFact("Saturn V first stage", "built_by", "Boeing"),
        ],
    )
    assert target.intent == "manufacturer"
    assert target.canonical_relation == "built_by"


def test_condition_claims_preserves_on_target_triple():
    question = "Where was Apollo 11 crew member Neil Armstrong born?"
    target = derive_question_target(question, APOLLO_FACTS)
    raw = Triple("Neil Armstrong", "born_in", "Wapakoneta")
    conditioned = condition_claims_to_question(
        [raw],
        question,
        "Wapakoneta",
        target,
        APOLLO_FACTS,
    )
    assert conditioned[0].subject == "Neil Armstrong"
    assert conditioned[0].relation == "born_in"
    assert conditioned[0].object == "Wapakoneta"


INTENT_CASES = [
    ("Who crewed Apollo 11?", "crew_members"),
    ("Where was Apollo 11 launched from?", "launch_site"),
    ("When was the Apollo 11 mission?", "occurrence_date"),
    ("Which company built the Saturn V first stage?", "manufacturer"),
    ("Which state contains Wapakoneta?", "location_containment"),
    ("Which country contains Ohio?", "location_containment"),
    ("Which person led Country Eta?", "leader"),
    ("Which vehicle launched Apollo 11?", "launch_vehicle"),
    ("Which organization built Stage Gamma?", "manufacturer"),
    ("How much lunar material was collected?", "collection_amount"),
    (
        "Where was Apollo 11 crew member Neil Armstrong born?",
        "birthplace",
    ),
    (
        "In which town was the Apollo 11 crew member Neil Armstrong born?",
        "birthplace",
    ),
    # Qualifiers that must not hijack a clinical target.
    (
        "Which medication was discontinued for the Apollo-like Patient Case A?",
        "medication_discontinued",
    ),
    (
        "What is the A1c for Patient Case A with Apollo 11 crew member chart notes?",
        "lab_measurement",
    ),
]


def test_broad_interrogative_intent_selection():
    for question, expected in INTENT_CASES:
        target = derive_question_target(question, APOLLO_FACTS)
        assert target.intent == expected, (question, target.intent, expected)


def test_interrogative_frame_prefers_final_predicate_over_qualifier():
    frame = parse_interrogative_frame(
        "In which town was the Apollo 11 crew member Neil Armstrong born?"
    )
    assert frame.wh_word == "which"
    assert frame.head_noun == "town"
    assert frame.predicate == "born"
