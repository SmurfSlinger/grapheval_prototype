"""Tests for decomposed iterative KGc backtracking."""

from __future__ import annotations

import pytest

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import KgcFact, KgcProvenanceType, SubQuestionStopReason
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.context_triple_extractor import ContextTripleExtractor
from src.pipeline.kgc_iteration import determine_stop_reason
from src.pipeline.structured_output import KgcExtractionError
from src.pipeline.sub_answer_combiner import combine_sub_answers
from src.pipeline.working_kgc import WorkingKgcState
from src.pipeline.backtracking_runner import BacktrackingRunner


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def test_stable_apollo_demo_regression():
    result = BacktrackingRunner(MockProvider(), max_iterations=1).run_example(
        _example("saturn_v_apollo_11_001")
    )
    assert len(result.kgc_facts) == 5
    assert len(result.extracted_claims) == 4
    assert result.supported_count == 1
    assert result.contradicted_count == 3
    assert result.no_evidence_count == 0


def test_decomposed_runner_splits_and_processes_sub_questions():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=2,
    )
    result = runner.run_example(_example("saturn_v_apollo_11_001"))

    assert len(result.sub_questions) == 4
    assert len(result.sub_question_results) == 4
    assert result.combined_answer.strip()
    assert len(result.base_kgc_facts) == 5
    assert len(result.working_kgc_facts) >= 5


def test_apollo_complex_exercises_decomposed_path():
    runner = DecomposedBacktrackingRunner(MockProvider(), max_iterations_per_sub_question=2)
    result = runner.run_example(_example("apollo_complex"))

    assert len(result.sub_questions) == 5
    assert result.metrics is not None
    assert result.metrics.sub_question_count == 5


def test_resolved_stop_condition():
    stop, _ = determine_stop_reason(
        iteration=0,
        max_iterations=3,
        current_answer="Supported answer",
        previous_answer=None,
        previous_signature=None,
        current_signature="sig",
        supported_count=1,
        contradicted_count=0,
        no_evidence_count=0,
        claim_count=1,
    )
    assert stop == SubQuestionStopReason.RESOLVED


def test_stalled_stop_condition():
    stop, _ = determine_stop_reason(
        iteration=1,
        max_iterations=3,
        current_answer="Same answer",
        previous_answer="Same answer",
        previous_signature="sig-a",
        current_signature="sig-b",
        supported_count=0,
        contradicted_count=1,
        no_evidence_count=0,
        claim_count=1,
    )
    assert stop == SubQuestionStopReason.STALLED


def test_max_iterations_stop_condition():
    stop, _ = determine_stop_reason(
        iteration=2,
        max_iterations=3,
        current_answer="Still wrong",
        previous_answer="Old",
        previous_signature="sig-a",
        current_signature="sig-b",
        supported_count=0,
        contradicted_count=2,
        no_evidence_count=0,
        claim_count=2,
    )
    assert stop == SubQuestionStopReason.MAX_ITERATIONS


def test_unresolved_no_evidence_stop_condition():
    stop, _ = determine_stop_reason(
        iteration=2,
        max_iterations=3,
        current_answer="Unknown detail",
        previous_answer="Old",
        previous_signature="sig-a",
        current_signature="sig-b",
        supported_count=0,
        contradicted_count=0,
        no_evidence_count=1,
        claim_count=1,
    )
    assert stop == SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE


def test_combined_answer_preserves_sub_answer_content():
    from src.models import SubQuestionResult

    results = [
        SubQuestionResult(
            sub_question_id=1,
            question="Q1",
            initial_answer="A0",
            final_answer="Resolved rocket answer",
            stop_reason=SubQuestionStopReason.RESOLVED,
            iteration_count=1,
        ),
        SubQuestionResult(
            sub_question_id=2,
            question="Q2",
            initial_answer="A0",
            final_answer="Partial answer",
            stop_reason=SubQuestionStopReason.STALLED,
            iteration_count=2,
        ),
    ]
    combined = combine_sub_answers(results)
    assert "Resolved rocket answer" in combined
    assert "Partial answer" in combined


def test_unvalidated_claims_not_auto_promoted_into_kgc():
    state = WorkingKgcState([KgcFact("Apollo 11", "launched_by", "Saturn V")])
    assert len(state.working_kgc) == 1

    from src.models import KgcClaimLabel, KgcEvaluationResult, Triple

    evaluation = KgcEvaluationResult(
        triple=Triple("Apollo 11", "launched_from", "Cape Canaveral"),
        label=KgcClaimLabel.SUPPORTED,
        reason="test",
        evidence="test",
    )
    state.record_evaluation(evaluation, sub_question_id=1, iteration=0)

    assert len(state.working_kgc) == 1
    assert state.candidate_updates
    assert state.candidate_updates[-1].promoted is False


def test_generation_failed_stop_for_refusal_answer():
    stop, _ = determine_stop_reason(
        iteration=0,
        max_iterations=3,
        current_answer="I do not have enough information to answer.",
        previous_answer=None,
        previous_signature=None,
        current_signature="",
        supported_count=0,
        contradicted_count=0,
        no_evidence_count=0,
        claim_count=0,
    )
    assert stop == SubQuestionStopReason.GENERATION_FAILED


def test_no_claims_extracted_stop_for_empty_claims():
    stop, _ = determine_stop_reason(
        iteration=1,
        max_iterations=2,
        current_answer="Some non-refusal answer without extractable claims.",
        previous_answer="Earlier answer",
        previous_signature="",
        current_signature="",
        supported_count=0,
        contradicted_count=0,
        no_evidence_count=0,
        claim_count=0,
    )
    assert stop == SubQuestionStopReason.NO_CLAIMS_EXTRACTED


def test_kgc_extraction_failure_stops_decomposed_run():
    from src.pipeline.structured_output import KgcExtractionError, StructuredExtractionTrace

    class FailingExtractor(ContextTripleExtractor):
        def extract_with_trace(self, context: str):
            raise KgcExtractionError(
                "Context triple extraction failed: bad csv",
                trace=StructuredExtractionTrace(stage="context_triple_extraction"),
            )

    runner = DecomposedBacktrackingRunner(MockProvider(), max_iterations_per_sub_question=2)
    runner._context_extractor = FailingExtractor(MockProvider())
    with pytest.raises(KgcExtractionError):
        runner.run_example(_example("apollo_complex"))


def test_sub_answer_generation_receives_trusted_context():
    captured: list[str] = []

    class CaptureProvider(MockProvider):
        def complete(self, prompt: str) -> str:
            captured.append(prompt)
            return super().complete(prompt)

    runner = DecomposedBacktrackingRunner(
        CaptureProvider(),
        max_iterations_per_sub_question=1,
        answer_0_mode="context_grounded_per_subquestion",
    )
    example = _example("apollo_complex")
    runner.run_example(example)

    answer_prompts = [
        p
        for p in captured
        if "Current sub-question:" in p
        and "Trusted context:" in p
        and "answer only the current sub-question" in p.lower()
    ]
    assert answer_prompts, "Expected context-grounded sub-question answer prompts"
    for prompt in answer_prompts:
        assert example.context[:80] in prompt
        assert "answer only the current sub-question" in prompt.lower()


def test_decomposed_trace_records_provider_class():
    runner = DecomposedBacktrackingRunner(MockProvider(), max_iterations_per_sub_question=1)
    result = runner.run_example(_example("saturn_v_apollo_11_001"))
    assert result.trace is not None
    assert result.trace.provider_class == "MockProvider"
    assert result.trace.stage_providers["answer_generator"] == "MockProvider"
    assert result.trace.stage_providers["focused_extractor"] == "MockProvider"
