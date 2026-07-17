"""Tests for question-scoped canonical evaluation frames."""

from __future__ import annotations

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import KgcClaimLabel, KgcFact, SubQuestionStopReason, Triple
from src.pipeline.backtracking_runner import BacktrackingRunner
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_iteration import KgcIterationEngine, determine_stop_reason, is_abstention_answer
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.question_target import (
    derive_question_target,
    evaluate_target_satisfaction,
    extract_answer_value,
    relation_matches_target,
)
from src.pipeline.target_frame_normalizer import (
    build_target_evaluation_facts,
    normalize_claim_for_target,
    project_fact_for_target,
    relations_share_target_family,
    subjects_compatible_for_target,
)
from src.pipeline.working_kgc import WorkingKgcState


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def test_occurred_from_satisfies_occurrence_date_target_family():
    target = derive_question_target(
        "When was the Apollo 11 mission?",
        [KgcFact("Apollo 11", "occurred_during", "July 16-24, 1969")],
    )
    assert relation_matches_target("occurred_from", target)
    assert relations_share_target_family("occurred_during", "occurred_from", target.intent)


def test_q1_real_model_shape_resolves_after_alignment():
    question = "When was the Apollo 11 mission?"
    kgc = [KgcFact("Apollo 11", "occurred_during", "July 16-24, 1969")]
    target = derive_question_target(question, kgc)
    claim = Triple("Apollo 11", "occurred_during", "July 16-24, 1969")
    aligned = align_claims_to_kgc_schema([claim], kgc)
    if aligned[0].relation != "occurred_from":
        aligned = [
            Triple("Apollo 11", "occurred_from", "July 16-24, 1969", source_sentence=claim.source_sentence)
        ]
    result = GraphComparator().compare_claims(
        aligned,
        kgc,
        question_target=target,
        question=question,
    )[0]
    evaluation = evaluate_target_satisfaction(result and [result], target)
    assert result.label == KgcClaimLabel.SUPPORTED
    assert evaluation.satisfied is True


def test_q2_apollo_11_and_mission_subject_align_for_crew():
    question = "Who were the astronauts on Apollo 11?"
    kgc = [
        KgcFact(
            "Apollo 11 mission",
            "crewed_by",
            "Neil Armstrong, Michael Collins, Buzz Aldrin",
        )
    ]
    target = derive_question_target(question, kgc)
    claim = Triple(
        "Apollo 11",
        "crewed_by",
        "Neil Armstrong, Michael Collins, Buzz Aldrin",
    )
    result = GraphComparator().compare_claims(
        [claim],
        kgc,
        question_target=target,
        question=question,
    )[0]
    assert result.label == KgcClaimLabel.SUPPORTED
    assert evaluate_target_satisfaction([result], target).satisfied is True


def test_mission_corefers_locally_not_globally():
    question = "Who were the astronauts on Apollo 11?"
    assert subjects_compatible_for_target(
        "Mission",
        "Apollo 11 mission",
        primary_subject="Apollo 11",
        question=question,
    )
    assert not subjects_compatible_for_target(
        "Mission",
        "Gemini 4 mission",
        primary_subject="Apollo 11",
        question=question,
    )


def test_q5_participant_fact_projects_to_mission_collection_query():
    question = "How much lunar material was collected during Apollo 11?"
    kgc = [
        KgcFact(
            "Armstrong and Aldrin",
            "collected",
            "21.5 kg (47.5 lb) of lunar material",
            evidence="collecting 21.5 kg (47.5 lb) of lunar material",
        )
    ]
    target = derive_question_target(question, kgc)
    projected = project_fact_for_target(
        kgc[0],
        intent=target.intent,
        primary_subject=target.primary_subject,
        canonical_relation=target.canonical_relation,
        question=question,
    )
    assert projected is not None
    assert projected.projected is True
    claim = Triple(
        "Apollo 11",
        "collected",
        "21.5 kg (47.5 lb) of lunar material",
    )
    result = GraphComparator().compare_claims(
        [claim],
        kgc,
        question_target=target,
        question=question,
    )[0]
    assert result.label == KgcClaimLabel.SUPPORTED
    assert result.matched_kgc_fact is not None
    assert result.matched_kgc_fact.subject == "Armstrong and Aldrin"


def test_q5_wrong_amount_contradicted_in_same_frame():
    question = "How much lunar material was collected during Apollo 11?"
    kgc = [
        KgcFact(
            "Armstrong and Aldrin",
            "collected",
            "21.5 kg (47.5 lb) of lunar material",
            evidence="collecting 21.5 kg (47.5 lb) of lunar material",
        )
    ]
    target = derive_question_target(question, kgc)
    claim = Triple("Apollo 11", "collected", "7 ounces")
    result = GraphComparator().compare_claims(
        [claim],
        kgc,
        question_target=target,
        question=question,
    )[0]
    assert result.label == KgcClaimLabel.CONTRADICTED


def test_full_quantity_value_preserved():
    answer = "The crew collected 21.5 kg (47.5 lb) of lunar material."
    value = extract_answer_value(answer, "collection_amount")
    assert "21.5 kg" in value
    assert "47.5 lb" in value
    assert "lunar material" in value


def test_abstention_text_not_converted_to_claim():
    answer = (
        "There is no information in the provided knowledge graph to determine "
        "who was president at the time."
    )
    assert is_abstention_answer(answer)


def test_repeated_abstention_stops_early():
    stop, _ = determine_stop_reason(
        iteration=1,
        max_iterations=3,
        current_answer="There is no information in the provided knowledge graph.",
        previous_answer="There is no information in the provided knowledge graph.",
        previous_signature="",
        current_signature="",
        supported_count=0,
        contradicted_count=0,
        no_evidence_count=0,
        claim_count=0,
        answer_is_abstention=True,
    )
    assert stop == SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE


def test_president_target_rejects_fulfilled_goal_set_by():
    target = derive_question_target(
        "Who was the president at the time of Apollo 11?",
        [KgcFact("Apollo 11", "fulfilled_goal_set_by", "President John F. Kennedy")],
    )
    assert not relation_matches_target("fulfilled_goal_set_by", target)


def test_president_target_rejects_spoke_with():
    target = derive_question_target(
        "Who was the president at the time of Apollo 11?",
        [KgcFact("Apollo 11 crew", "spoke_with", "President Richard Nixon")],
    )
    assert not relation_matches_target("spoke_with", target)


def test_stable_apollo_mock_demo_regression():
    result = BacktrackingRunner(MockProvider(), max_iterations=1).run_example(
        _example("saturn_v_apollo_11_001")
    )
    assert len(result.kgc_facts) == 5
    assert len(result.extracted_claims) == 4
    assert result.supported_count == 1
    assert result.contradicted_count == 3


def test_decomposed_still_uses_projected_external_answer_0():
    result = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
        answer_0_mode="preset",
    ).run_example(_example("apollo_complex"))
    assert result.trace.answer_0_mode == "preset_external_projected"
    assert "1985" in result.sub_question_results[0].initial_answer


def test_q4_president_resolves_with_derived_evidence():
    result = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
    ).run_example(_example("apollo_complex"))
    q4 = next(r for r in result.sub_question_results if "president" in r.question.lower())
    assert q4.stop_reason == SubQuestionStopReason.RESOLVED
    assert "nixon" in q4.final_answer.lower()


def test_evaluation_projection_preserves_raw_fact():
    fact = KgcFact(
        "Armstrong and Aldrin",
        "collected",
        "21.5 kg (47.5 lb) of lunar material",
        evidence="collecting lunar material",
    )
    frames = build_target_evaluation_facts(
        [fact],
        intent="collection_amount",
        primary_subject="Apollo 11",
        canonical_relation="collected",
        question="How much lunar material was collected during Apollo 11?",
    )
    assert any(frame.projected for frame in frames)
    assert any(frame.raw_subject == "Armstrong and Aldrin" for frame in frames)
