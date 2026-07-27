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


def test_interrogative_frame_prefers_main_clause_predicate_over_qualifier():
    frame = parse_interrogative_frame(
        "In which town was the Apollo 11 crew member Neil Armstrong born?"
    )
    assert frame.wh_word == "which"
    assert frame.head_noun == "town"
    assert frame.predicate == "born"


def test_nested_headquarters_frame_ignores_launched_qualifier():
    frame = parse_interrogative_frame(
        "In which city is the company headquartered that built the first stage "
        "of the rocket that launched Mission Alpha?"
    )
    assert frame.head_noun == "city"
    assert frame.predicate == "headquartered"
    target = derive_question_target(
        "In which city is the company headquartered that built the first stage "
        "of the rocket that launched Mission Alpha?",
        [
            KgcFact("Company Delta", "headquartered_in", "City Epsilon"),
            KgcFact("Mission Alpha", "launched_by", "Rocket Beta"),
        ],
    )
    assert target.intent == "headquarters"


def test_nested_birthplace_frame_ignores_deeper_headquartered_qualifier():
    question = (
        "In which town was the person born who leads the country that contains "
        "the state that contains the city where the company is headquartered?"
    )
    frame = parse_interrogative_frame(question)
    assert frame.head_noun == "town"
    assert frame.predicate == "born"
    assert derive_question_target(question, []).intent == "birthplace"


def test_capital_of_frame_selects_capital_city():
    question = "What is the capital of the region that contains Town Iota?"
    frame = parse_interrogative_frame(question)
    assert frame.head_noun == "capital"
    assert frame.predicate == "capital"
    assert derive_question_target(question, []).intent == "capital_city"


def test_river_question_not_hijacked_by_capital_noun():
    question = (
        "Which river runs beside the capital of the country containing "
        "Neil Armstrong's birthplace?"
    )
    frame = parse_interrogative_frame(question)
    assert frame.head_noun == "river"
    assert frame.predicate != "capital"
    assert derive_question_target(question, []).intent != "capital_city"


def test_state_birthplace_question_is_location_not_crew():
    question = (
        "In which state is the birthplace of Apollo 11 crew member Neil Armstrong?"
    )
    frame = parse_interrogative_frame(question)
    assert frame.head_noun == "state"
    target = derive_question_target(question, APOLLO_FACTS)
    assert target.intent == "location_containment"


def test_condition_claims_uses_unique_trusted_fact_for_answer_value():
    facts = APOLLO_FACTS + [
        KgcFact("Wapakoneta", "located_in", "Ohio"),
        KgcFact("Ohio", "part_of", "United States"),
        KgcFact("United States", "has_capital", "Washington, D.C."),
    ]
    country_q = "Which country contains the state containing Neil Armstrong's birthplace?"
    country_target = derive_question_target(country_q, facts)
    conditioned = condition_claims_to_question(
        [Triple("United States", "contains", "Ohio")],
        country_q,
        "the United States",
        country_target,
        facts,
    )
    assert conditioned[0].subject == "Ohio"
    assert conditioned[0].object == "United States"

    capital_q = "What is the capital of the country containing Neil Armstrong's birthplace state?"
    capital_target = derive_question_target(capital_q, facts)
    assert capital_target.intent == "capital_city"
    capital_conditioned = condition_claims_to_question(
        [],
        capital_q,
        "Washington, D.C.",
        capital_target,
        facts,
    )
    assert capital_conditioned[0].subject == "United States"
    assert capital_conditioned[0].object == "Washington, D.C."
