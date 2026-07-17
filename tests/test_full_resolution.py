"""Full-resolution regression tests for decomposed iterative KGc."""

from __future__ import annotations

import pytest

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import KgcClaimLabel, KgcFact, SubQuestionStopReason, Triple
from src.pipeline.abstention_detection import is_abstention_answer
from src.pipeline.date_range_normalize import date_intervals_equivalent
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_iteration import KgcIterationEngine, determine_stop_reason
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.question_target import (
    condition_claims_to_question,
    derive_question_target,
    evaluate_target_satisfaction,
)
from src.pipeline.target_fact_deriver import TargetFactDeriver
from src.pipeline.working_kgc import WorkingKgcState


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


APOLLO_CONTEXT = _example("apollo_complex").context


def test_q1_occurred_between_supported_in_comparator():
    kgc = [KgcFact("Apollo 11", "occurred_between", "July 16-24, 1969")]
    claim = Triple("Apollo 11", "occurred_during", "July 16-24, 1969")
    target = derive_question_target("When was the Apollo 11 mission?", kgc)
    assert target.canonical_relation is not None
    result = GraphComparator().compare_claims(
        [claim], kgc, question_target=target, question="When was the Apollo 11 mission?"
    )[0]
    assert result.label == KgcClaimLabel.SUPPORTED


def test_q1_wrong_date_contradicted_in_comparator():
    kgc = [KgcFact("Apollo 11", "occurred_between", "July 16-24, 1969")]
    claim = Triple("Apollo 11", "occurred_during", "july 16-august 5, 1985")
    target = derive_question_target("When was the Apollo 11 mission?", kgc)
    result = GraphComparator().compare_claims(
        [claim], kgc, question_target=target, question="When was the Apollo 11 mission?"
    )[0]
    assert result.label == KgcClaimLabel.CONTRADICTED


@pytest.mark.parametrize(
    ("left", "right", "equivalent"),
    [
        ("July 16-24, 1969", "July 16 through July 24, 1969", True),
        ("July 16-24, 1969", "between July 16 and July 24, 1969", True),
        ("july 16-august 5, 1985", "July 16-24, 1969", False),
        ("July 16-August 5, 1969", "July 16-24, 1969", False),
    ],
)
def test_date_interval_comparator_equivalence(left: str, right: str, equivalent: bool):
    assert date_intervals_equivalent(left, right) is equivalent
    kgc = [KgcFact("Mission", "occurred_between", right)]
    claim = Triple("Mission", "occurred_during", left)
    target = derive_question_target("When was the mission?", kgc)
    result = GraphComparator().compare_claims(
        [claim], kgc, question_target=target, question="When was the mission?"
    )[0]
    if equivalent:
        assert result.label == KgcClaimLabel.SUPPORTED
    else:
        assert result.label == KgcClaimLabel.CONTRADICTED


def test_q4_canonical_relation_never_none():
    target = derive_question_target(
        "Who was the president at the time of the mission?",
        [KgcFact("Mission", "launched_by", "Rocket")],
    )
    assert target.intent == "president_at_time"
    assert target.canonical_relation == "president_at_time"
    claims = condition_claims_to_question(
        [],
        "Who was the president at the time of the mission?",
        "Donald Trump",
        target,
        [],
    )
    assert len(claims) == 1
    assert claims[0].relation == "president_at_time"
    assert claims[0].relation is not None


def test_q4_derives_nixon_not_kennedy():
    kgc = [
        KgcFact(
            "Apollo 11 crew",
            "spoke_with",
            "President Richard Nixon",
            evidence="speaking by telephone with President Richard Nixon",
        )
    ]
    target = derive_question_target(
        "Who was the president at the time of the Apollo 11 mission?",
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    derived, trace = TargetFactDeriver().derive(
        question="Who was the president at the time of the Apollo 11 mission?",
        trusted_context=APOLLO_CONTEXT,
        target=target,
        kgc_facts=kgc,
    )
    assert trace.attempted
    assert len(derived) == 1
    assert "nixon" in derived[0].object.lower()
    assert "kennedy" not in derived[0].object.lower()
    assert derived[0].relation == "president_at_time"


def test_q4_spoke_with_not_equivalent_to_president_at_time():
    kgc = [KgcFact("Apollo 11 crew", "spoke_with", "President Richard Nixon")]
    claim = Triple("Apollo 11", "president_at_time", "Donald Trump")
    target = derive_question_target(
        "Who was the president at the time?",
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    result = GraphComparator().compare_claims(
        [claim], kgc, question_target=target, question="Who was the president at the time?"
    )[0]
    assert result.label == KgcClaimLabel.NO_EVIDENCE


def test_q4_evaluation_contradiction_after_derivation():
    kgc = [
        KgcFact("Apollo 11", "president_at_time", "Richard Nixon", evidence="telephone with President Richard Nixon")
    ]
    claim = Triple("Apollo 11", "president_at_time", "Donald Trump")
    target = derive_question_target(
        "Who was the president at the time?",
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    result = GraphComparator().compare_claims(
        [claim], kgc, question_target=target, question="Who was the president at the time?"
    )[0]
    assert result.label == KgcClaimLabel.CONTRADICTED


def test_q4_supported_after_correction():
    kgc = [
        KgcFact("Apollo 11", "president_at_time", "Richard Nixon", evidence="telephone with President Richard Nixon")
    ]
    claim = Triple("Apollo 11", "president_at_time", "Richard Nixon")
    target = derive_question_target(
        "Who was the president at the time?",
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    evaluated = GraphComparator().compare_claims(
        [claim], kgc, question_target=target, question="Who was the president at the time?"
    )
    target_eval = evaluate_target_satisfaction(evaluated, target)
    assert evaluated[0].label == KgcClaimLabel.SUPPORTED
    assert target_eval.satisfied


def test_schema_aligner_preserves_president_target_relation():
    kgc = [KgcFact("Apollo 11 crew", "spoke_with", "President Richard Nixon")]
    claim = Triple("Apollo 11", "president_at_time", "Richard Nixon")
    target = derive_question_target(
        "Who was the president at the time?",
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    aligned = align_claims_to_kgc_schema([claim], kgc, question_target=target)[0]
    assert aligned.relation == "president_at_time"


def test_no_evidence_found_is_abstention():
    assert is_abstention_answer("No evidence found.")


def test_factual_negation_not_abstention():
    assert not is_abstention_answer("Apollo 11 did not launch from Florida")


def test_q5_collection_regression():
    kgc = [KgcFact("Apollo 11", "collected", "21.5 kg (47.5 lb) of lunar material")]
    claim = Triple("Apollo 11", "collected", "21.5 kg (47.5 lb) of lunar material")
    target = derive_question_target(
        "How much lunar material was collected during the mission?",
        kgc,
    )
    result = GraphComparator().compare_claims(
        [claim],
        kgc,
        question_target=target,
        question="How much lunar material was collected during the mission?",
    )[0]
    assert result.label == KgcClaimLabel.SUPPORTED


def test_mock_decomposed_apollo_complex_five_of_five():
    result = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
        answer_0_mode="preset",
    ).run_example(_example("apollo_complex"))
    resolved = [
        sub
        for sub in result.sub_question_results
        if sub.stop_reason == SubQuestionStopReason.RESOLVED
    ]
    assert len(resolved) == 5
    q4 = next(r for r in result.sub_question_results if "president" in r.question.lower())
    assert any(
        item.provenance.value == "derived_from_trusted_context"
        for item in result.working_kgc_additions
        if item.fact.relation == "president_at_time"
    ) or any(
        h.derived_facts_added
        for h in q4.iteration_history
    )


def test_q4_iteration_derives_and_resolves():
    example = _example("apollo_complex")
    state = WorkingKgcState([KgcFact("Apollo 11", "launched_by", "Saturn V")])
    _, history, stop, _ = KgcIterationEngine(MockProvider()).run_sub_question(
        question="Who was the president at the time of the Apollo 11 mission?",
        trusted_context=example.context,
        working_state=state,
        sub_question_id=4,
        initial_answer="Donald Trump",
        max_iterations=3,
    )
    assert stop == SubQuestionStopReason.RESOLVED
    assert any(h.derived_facts_added for h in history)
    assert "nixon" in history[-1].answer.lower()
