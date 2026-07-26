"""Tests for compound Answer(0) projection onto sub-questions."""

from __future__ import annotations

import pytest

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import KgcClaimLabel, KgcProvenanceType, SubQuestion, SubQuestionStopReason
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.structured_output import StructuredOutputError, parse_sub_answer_projection_response
from src.pipeline.sub_answer_projector import SubAnswerProjector
from src.pipeline.working_kgc import WorkingKgcState
from src.models import KgcFact, Triple
from src.pipeline.backtracking_runner import BacktrackingRunner


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def test_malformed_projection_json_retries_or_fails():
    class TwoAttemptProvider:
        def __init__(self) -> None:
            self.projection_calls = 0

        def complete(self, prompt: str) -> str:
            if "Project the compound Answer(0)" not in prompt:
                raise RuntimeError("unexpected prompt")
            self.projection_calls += 1
            if self.projection_calls == 1:
                return '{"answers": [{"id": 1, "answer": "july 16-august 5, 1985"}]}'
            return (
                '{"answers": [{"id": 1, "answer": "july 16-august 5, 1985"}, '
                '{"id": 2, "answer": "Neil Armstrong"}]}'
            )

    provider = TwoAttemptProvider()
    projector = SubAnswerProjector(provider)
    sub_questions = [
        SubQuestion(id=1, question="When was the Apollo 11 mission?"),
        SubQuestion(id=2, question="Who were the astronauts?"),
    ]
    answers, trace = projector.project(
        "When was Apollo 11? Who were the astronauts?",
        sub_questions,
        "The mission ran july 16-august 5, 1985 and Neil Armstrong was on board.",
        use_deterministic_labeled_fields=False,
    )
    assert len(answers) == 2
    assert trace.retry_count == 1
    assert provider.projection_calls == 2


def test_grounding_uses_full_answer_for_single_claim_sub_answer():
    from src.pipeline.claim_grounding import ground_claim_objects_in_answer

    answer = "John F Kennedy Airport"
    claims = [
        Triple(
            "Apollo 11",
            "launched_from",
            "Kennedy Space Center in Florida",
        )
    ]
    grounded, _ = ground_claim_objects_in_answer(claims, answer)
    assert grounded[0].object == answer


def test_grounding_replaces_kgc_leaked_object_with_source_sentence():
    from src.pipeline.claim_grounding import ground_claim_objects_in_answer

    answer = "july 16-august 5, 1985"
    claims = [
        Triple(
            "Apollo 11",
            "occurred_during",
            "July 16-24, 1969",
            source_sentence="july 16-august 5, 1985",
        )
    ]
    grounded, _ = ground_claim_objects_in_answer(claims, answer)
    assert "1985" in grounded[0].object


def test_stable_apollo_demo_regression():
    result = BacktrackingRunner(MockProvider(), max_iterations=1).run_example(
        _example("saturn_v_apollo_11_001")
    )
    assert len(result.kgc_facts) == 5
    assert len(result.extracted_claims) == 4
    assert result.supported_count == 1
    assert result.contradicted_count == 3
    assert result.no_evidence_count == 0


def test_projection_parser_requires_exact_ids():
    parsed = parse_sub_answer_projection_response(
        '{"answers": [{"id": 1, "answer": "A1"}, {"id": 2, "answer": "A2"}]}',
        [1, 2],
    )
    assert len(parsed) == 2
    with pytest.raises(StructuredOutputError):
        parse_sub_answer_projection_response(
            '{"answers": [{"id": 1, "answer": "A1"}]}',
            [1, 2],
        )


def test_preset_compound_answer_projected_not_regenerated():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
        answer_0_mode="preset",
    )
    example = _example("apollo_complex")
    result = runner.run_example(example)

    assert result.trace is not None
    assert result.trace.answer_0_mode == "preset_external_projected"
    assert result.metrics is not None
    assert "1985" in result.metrics.compound_answer_0
    q1 = result.sub_question_results[0]
    assert "1985" in q1.initial_answer


def test_projector_preserves_factual_errors():
    provider = MockProvider()
    projector = SubAnswerProjector(provider)
    example = _example("apollo_complex")
    sub_questions = [
        SubQuestion(id=1, question="When was the Apollo 11 mission?"),
        SubQuestion(id=2, question="Who were the astronauts?"),
        SubQuestion(id=3, question="Where was it launched from?"),
        SubQuestion(id=4, question="Who was the president?"),
        SubQuestion(id=5, question="How much lunar material was collected?"),
    ]
    answers, trace = projector.project(
        example.question,
        sub_questions,
        example.initial_answer or "",
    )
    assert trace.method == "deterministic_labeled_fields"
    assert trace.faithfulness_passed is True
    by_id = {item.sub_question_id: item.answer for item in answers}
    assert "1985" in by_id[1]
    assert "jessica" in by_id[2].lower()
    assert "airport" in by_id[3].lower()
    assert "trump" in by_id[4].lower()
    assert "7 ounce" in by_id[5].lower()


def test_every_sub_question_receives_one_projected_answer():
    runner = DecomposedBacktrackingRunner(MockProvider(), max_iterations_per_sub_question=2)
    result = runner.run_example(_example("apollo_complex"))
    assert len(result.sub_question_results) == len(result.sub_questions)
    for sub in result.sub_question_results:
        assert sub.initial_answer.strip()


def test_q1_wrong_date_contradiction_resolves_after_revision():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
    )
    result = runner.run_example(_example("apollo_complex"))
    q1 = next(r for r in result.sub_question_results if r.sub_question_id == 1)
    assert q1.initial_contradicted >= 1
    assert "1969" in q1.final_answer
    assert q1.stop_reason == SubQuestionStopReason.RESOLVED
    assert q1.revision_count >= 1


def test_q3_wrong_launch_site_corrected_after_focused_enrichment():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
    )
    result = runner.run_example(_example("apollo_complex"))
    q3 = next(
        r for r in result.sub_question_results if "launch" in r.question.lower()
    )
    assert "airport" in q3.initial_answer.lower()
    assert "kennedy" in q3.final_answer.lower()
    assert q3.final_supported >= 1


def test_q5_wrong_quantity_corrected_and_reevaluated():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
    )
    result = runner.run_example(_example("apollo_complex"))
    q5 = next(
        r for r in result.sub_question_results if "lunar material" in r.question.lower()
    )
    assert "7 ounce" in q5.initial_answer.lower()
    assert "21.5" in q5.final_answer
    assert q5.initial_contradicted >= 1
    assert q5.stop_reason == SubQuestionStopReason.RESOLVED


def test_generated_claims_not_inserted_as_trusted_facts():
    runner = DecomposedBacktrackingRunner(MockProvider(), max_iterations_per_sub_question=2)
    result = runner.run_example(_example("apollo_complex"))
    assert all(not update.promoted for update in result.candidate_kgc_updates)


def test_derived_provenance_type_exists():
    assert hasattr(KgcProvenanceType, "DERIVED_FROM_TRUSTED_CONTEXT")


def test_spoke_with_does_not_align_to_president_at_time():
    kgc = [KgcFact("Apollo 11 crew", "spoke_with", "President Richard Nixon")]
    claim = Triple("Apollo 11", "president_at_time", "Donald Trump")
    aligned = align_claims_to_kgc_schema([claim], kgc)[0][0]
    assert aligned.relation == "president_at_time"
    assert aligned.object == "Donald Trump"


def test_focused_extractor_prefers_minimal_date_fact():
    provider = MockProvider()
    from src.pipeline.relevant_context_fact_extractor import RelevantContextFactExtractor

    example = _example("apollo_complex")
    facts, _ = RelevantContextFactExtractor(provider).extract_with_trace(
        "When was the Apollo 11 mission?",
        example.context,
    )
    assert len(facts) == 1
    assert facts[0].relation in {"occurred_during", "occurred_between"}


def test_subject_deduplication_strips_leading_article():
    state = WorkingKgcState(
        [KgcFact("The mission", "crewed_by", "Neil Armstrong, Michael Collins, Buzz Aldrin")]
    )
    added = state.merge_focused_facts(
        [KgcFact("mission", "crewed_by", "Neil Armstrong, Michael Collins, Buzz Aldrin")],
        sub_question_id=2,
    )
    assert added == []
    assert len(state.working_kgc) == 1


def test_correction_metrics_track_initial_and_revisions():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
    )
    result = runner.run_example(_example("apollo_complex"))
    metrics = result.metrics
    assert metrics is not None
    assert metrics.total_initial_contradicted >= 2
    assert metrics.total_revisions >= 3
    assert metrics.resolved_after_revision_count >= 2
