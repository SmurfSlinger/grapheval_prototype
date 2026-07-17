"""Tests for question-target compatibility and question-conditioned claims."""

from __future__ import annotations

import pytest

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import (
    KgcClaimLabel,
    KgcEvaluationResult,
    KgcFact,
    SubQuestionStopReason,
    Triple,
)
from src.pipeline.backtracking_runner import BacktrackingRunner
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.question_target import (
    condition_claims_to_question,
    dedupe_minimal_claims,
    derive_question_target,
    evaluate_target_satisfaction,
    extract_answer_value,
)
from src.pipeline.relevant_context_fact_extractor import RelevantContextFactExtractor
from src.pipeline.triple_extractor import TripleExtractor


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def _target(question: str, kgc: list[KgcFact] | None = None):
    return derive_question_target(question, kgc or [KgcFact("Apollo 11", "occurred_during", "July 16-24, 1969")])


def test_claim_extraction_receives_sub_question_and_answer():
    provider = MockProvider()
    extractor = TripleExtractor(provider)
    question = "When was the Apollo 11 mission?"
    answer = "July 16-August 5, 1985."
    kgc = [KgcFact("Apollo 11", "occurred_during", "July 16-24, 1969")]
    extracted, aligned = extractor.extract_kgc_claims(
        answer,
        kgc_facts=kgc,
        question=question,
    )
    assert extracted
    assert extracted[0].relation == "occurred_during"
    assert "1985" in extracted[0].object


def test_wrong_date_grounded_to_date_relation():
    target = _target("When was the Apollo 11 mission?")
    claims = condition_claims_to_question(
        [Triple("Mission dates", "are", "July 16-August 5, 1985")],
        "When was the Apollo 11 mission?",
        "July 16-August 5, 1985.",
        target,
        [KgcFact("Apollo 11", "occurred_during", "July 16-24, 1969")],
    )
    assert claims[0].relation == "occurred_during"
    assert "1985" in claims[0].object


def test_wrong_crew_grounded_to_crewed_by():
    target = _target(
        "Who were the astronauts on Apollo 11?",
        [KgcFact("Apollo 11", "crewed_by", "Neil Armstrong, Michael Collins, Buzz Aldrin")],
    )
    claims = condition_claims_to_question(
        [Triple("Neil Armstrong", "was_part_of", "Neil Armstrong, Jessica Davis, Buzz Lightyear")],
        "Who were the astronauts on Apollo 11?",
        "Neil Armstrong, Jessica Davis, Buzz Lightyear.",
        target,
        [KgcFact("Apollo 11", "crewed_by", "Neil Armstrong, Michael Collins, Buzz Aldrin")],
    )
    assert claims[0].relation == "crewed_by"
    assert "Jessica" in claims[0].object


def test_generic_who_crewed_question_maps_to_crew_relation_family():
    target = _target(
        "Who crewed Apollo 11?",
        [KgcFact("Apollo 11", "crewed_by", "Neil Armstrong")],
    )

    assert target.intent == "crew_members"
    assert "crewed_by" in target.expected_relations
    assert target.canonical_relation == "crewed_by"
    evaluation = evaluate_target_satisfaction(
        [
            KgcEvaluationResult(
                triple=Triple("Apollo 11", "crewed_by", "Neil Armstrong"),
                label=KgcClaimLabel.SUPPORTED,
                reason="Exact trusted fact.",
                evidence="Apollo 11 was crewed by Neil Armstrong.",
            )
        ],
        target,
    )
    assert evaluation.satisfied is True


def test_wrong_launch_site_remains_launched_from():
    target = _target(
        "Where was Apollo 11 launched from?",
        [KgcFact("Apollo 11", "launched_from", "Kennedy Space Center in Florida")],
    )
    claims = condition_claims_to_question(
        [],
        "Where was Apollo 11 launched from?",
        "John F Kennedy Airport.",
        target,
        [KgcFact("Apollo 11", "launched_from", "Kennedy Space Center in Florida")],
    )
    assert claims[0].relation == "launched_from"
    assert "Airport" in claims[0].object


def test_wrong_amount_grounded_to_collection_relation():
    target = _target(
        "How much lunar material was collected?",
        [KgcFact("Apollo 11", "lunar_material_collected", "21.5 kg")],
    )
    claims = condition_claims_to_question(
        [Triple("Apollo 11", "has_property", "7 ounces")],
        "How much lunar material was collected?",
        "7 ounces.",
        target,
        [KgcFact("Apollo 11", "lunar_material_collected", "21.5 kg")],
    )
    assert claims[0].relation == "lunar_material_collected"
    assert "7 ounce" in claims[0].object.lower()


def test_wrong_values_remain_unchanged_during_extraction():
    answer = "Donald Trump."
    target = _target("Who was the president at the time of Apollo 11?")
    claims = condition_claims_to_question(
        [],
        "Who was the president at the time of Apollo 11?",
        answer,
        target,
        [KgcFact("Apollo 11 crew", "spoke_with", "President Richard Nixon")],
    )
    assert claims[0].object == "Donald Trump"


def test_question_target_required_for_resolved():
    target = derive_question_target(
        "Who was the president at the time of Apollo 11?",
        [KgcFact("Apollo 11", "fulfilled_goal_set_by", "President John F. Kennedy")],
    )
    evaluation = evaluate_target_satisfaction(
        [
            KgcEvaluationResult(
                triple=Triple(
                    "Apollo 11",
                    "fulfilled_goal_set_by",
                    "President John F. Kennedy",
                ),
                label=KgcClaimLabel.SUPPORTED,
                reason="supported",
                evidence="evidence",
            )
        ],
        target,
    )
    assert evaluation.satisfied is False
    assert evaluation.supported_but_irrelevant_count == 1


def test_fulfilled_goal_set_by_does_not_satisfy_president_at_time():
    target = derive_question_target(
        "Who was the president at the time?",
        [KgcFact("Apollo 11", "fulfilled_goal_set_by", "President John F. Kennedy")],
    )
    assert "president_at_time" in target.expected_relations
    assert "fulfilled_goal_set_by" in target.excluded_relations


def test_spoke_with_does_not_equal_president_at_time():
    kgc = [KgcFact("Apollo 11 crew", "spoke_with", "President Richard Nixon")]
    claim = Triple("Apollo 11", "president_at_time", "Donald Trump")
    aligned = align_claims_to_kgc_schema([claim], kgc)[0]
    assert aligned.relation == "president_at_time"
    target = derive_question_target(
        "Who was the president at the time of Apollo 11?",
        kgc,
    )
    evaluation = evaluate_target_satisfaction(
        [
            KgcEvaluationResult(
                triple=Triple("Apollo 11 crew", "spoke_with", "President Richard Nixon"),
                label=KgcClaimLabel.SUPPORTED,
                reason="supported",
                evidence="evidence",
            )
        ],
        target,
    )
    assert evaluation.satisfied is False


def test_supported_irrelevant_claim_does_not_resolve_sub_question():
    """Spoke_with support must not satisfy president_at_time target."""
    kgc = [KgcFact("Apollo 11 crew", "spoke_with", "President Richard Nixon")]
    claim = Triple("Apollo 11", "president_at_time", "Donald Trump")
    target = derive_question_target(
        "Who was the president at the time?",
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    evaluated = GraphComparator().compare_claims(
        [claim], kgc, question_target=target, question="Who was the president at the time?"
    )
    target_eval = evaluate_target_satisfaction(evaluated, target)
    assert evaluated[0].label == KgcClaimLabel.NO_EVIDENCE
    assert not target_eval.satisfied


def test_terse_quantity_answer_produces_single_semantic_claim():
    provider = MockProvider()
    extractor = TripleExtractor(provider)
    question = "How much lunar material was collected by the Apollo 11 mission?"
    answer = "The crew collected 21.5 kg (47.5 lb) of lunar material."
    kgc = [
        KgcFact("Apollo 11", "lunar_material_collected", "21.5 kg"),
        KgcFact("Neil Armstrong", "collected", "21.5 kg (47.5 lb) of lunar material"),
    ]
    extracted, _ = extractor.extract_kgc_claims(
        answer,
        kgc_facts=kgc,
        question=question,
    )
    assert len(extracted) == 1


def test_focused_extractor_prefers_minimal_date_fact():
    provider = MockProvider()
    example = _example("apollo_complex")
    facts, _ = RelevantContextFactExtractor(provider).extract_with_trace(
        "When was the Apollo 11 mission?",
        example.context,
    )
    assert len(facts) == 1
    assert facts[0].relation in {"occurred_during", "occurred_between"}


def test_stable_apollo_mock_demo_regression():
    result = BacktrackingRunner(MockProvider(), max_iterations=1).run_example(
        _example("saturn_v_apollo_11_001")
    )
    assert len(result.kgc_facts) == 5
    assert len(result.extracted_claims) == 4
    assert result.supported_count == 1
    assert result.contradicted_count == 3
    assert result.no_evidence_count == 0


def test_decomposed_path_still_uses_projected_external_answer_0():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
        answer_0_mode="preset",
    )
    result = runner.run_example(_example("apollo_complex"))
    assert result.trace is not None
    assert result.trace.answer_0_mode == "preset_external_projected"
    q1 = result.sub_question_results[0]
    assert "1985" in q1.initial_answer


def test_wrong_date_initially_contradicted_with_question_target():
    provider = MockProvider()
    extractor = TripleExtractor(provider)
    question = "When was the Apollo 11 mission?"
    answer = "July 16-August 5, 1985."
    kgc = [KgcFact("Apollo 11", "occurred_during", "July 16-24, 1969")]
    _, aligned = extractor.extract_kgc_claims(answer, kgc_facts=kgc, question=question)
    evaluated = GraphComparator().compare_claims(aligned, kgc)
    assert evaluated[0].label == KgcClaimLabel.CONTRADICTED


def test_dedupe_minimal_claims_for_collection():
    target = derive_question_target(
        "How much lunar material was collected?",
        [KgcFact("Apollo 11", "lunar_material_collected", "21.5 kg")],
    )
    claims = dedupe_minimal_claims(
        [
            Triple("Neil Armstrong", "collected", "21.5 kg"),
            Triple("Neil Armstrong and Aldrin", "collected", "21.5 kg"),
        ],
        target,
        "21.5 kg",
    )
    assert len(claims) == 1


def test_extract_answer_value_strips_label_prefix():
    assert extract_answer_value("Mission dates: july 16-august 5, 1985.") == (
        "july 16-august 5, 1985"
    )
