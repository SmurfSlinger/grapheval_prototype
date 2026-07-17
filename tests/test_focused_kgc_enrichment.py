"""Tests for sub-question-directed trusted-context KGc enrichment."""

from __future__ import annotations

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import (
    KgcClaimLabel,
    KgcFact,
    KgcProvenanceType,
    KgcEvaluationResult,
    SubQuestionStopReason,
    Triple,
)
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.kgc_iteration import KgcIterationEngine, count_cumulative_evaluations
from src.pipeline.relevant_context_fact_extractor import RelevantContextFactExtractor
from src.pipeline.structured_output import StructuredExtractionTrace
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


def test_focused_extractor_receives_trusted_context_and_sub_question():
    captured: list[tuple[str, str]] = []

    class CaptureExtractor(RelevantContextFactExtractor):
        def extract_with_trace(
            self,
            question: str,
            trusted_context: str,
            *,
            existing_kgc_facts=None,
        ):
            captured.append((question, trusted_context))
            return super().extract_with_trace(
                question,
                trusted_context,
                existing_kgc_facts=existing_kgc_facts,
            )

    provider = MockProvider()
    runner = DecomposedBacktrackingRunner(provider, max_iterations_per_sub_question=1)
    runner._focused_extractor = CaptureExtractor(provider)
    runner._iteration_engine = KgcIterationEngine(
        provider,
        focused_extractor=runner._focused_extractor,
    )
    example = _example("apollo_complex")
    runner.run_example(example)

    assert captured
    for question, context in captured:
        assert question.strip()
        assert example.context[:80] in context


def test_focused_extraction_facts_tagged_trusted_context():
    state = WorkingKgcState([KgcFact("Apollo 11", "launched_by", "Saturn V")])
    added = state.merge_focused_facts(
        [KgcFact("Apollo 11", "launched_from", "Kennedy Space Center in Florida")],
        sub_question_id=3,
    )
    assert len(added) == 1
    addition = state.focused_additions[0]
    assert addition.provenance == KgcProvenanceType.TRUSTED_CONTEXT
    assert addition.extraction_scope == "sub_question_focused"
    assert addition.sub_question_id == 3


def test_identical_focused_facts_deduplicated():
    state = WorkingKgcState(
        [KgcFact("Apollo 11", "launched_from", "Kennedy Space Center in Florida")]
    )
    duplicate = KgcFact(
        "Apollo 11",
        "launched_from",
        "Kennedy Space Center in Florida",
    )
    assert state.merge_focused_facts([duplicate], sub_question_id=3) == []
    assert len(state.working_kgc) == 1


def test_generated_claims_not_auto_promoted():
    state = WorkingKgcState([KgcFact("Apollo 11", "launched_by", "Saturn V")])
    evaluation = KgcEvaluationResult(
        triple=Triple("Apollo 11", "launched_from", "Kennedy Space Center in Florida"),
        label=KgcClaimLabel.SUPPORTED,
        reason="test",
        evidence="test",
    )
    state.record_evaluation(evaluation, sub_question_id=3, iteration=0)
    assert len(state.working_kgc) == 1


class _StubFocusedExtractor:
    def extract_with_trace(
        self,
        question: str,
        trusted_context: str,
        *,
        existing_kgc_facts=None,
    ):
        _ = question, trusted_context, existing_kgc_facts
        fact = KgcFact(
            "Apollo 11",
            "launched_from",
            "Kennedy Space Center in Florida",
            evidence="from Kennedy Space Center in Florida",
        )
        return [fact], StructuredExtractionTrace(stage="relevant_context_extraction")


def test_no_evidence_triggers_focused_enrichment_before_revision():
    provider = MockProvider()
    working_state = WorkingKgcState(
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    engine = KgcIterationEngine(
        provider,
        focused_extractor=_StubFocusedExtractor(),
    )
    answer = "Launched from Kennedy Space Center in Florida."
    final_answer, history, stop_reason, _ = engine.run_sub_question(
        question="Where was Apollo 11 launched from?",
        trusted_context=_example("apollo_complex").context,
        working_state=working_state,
        sub_question_id=3,
        initial_answer=answer,
        max_iterations=2,
    )
    assert final_answer == answer
    assert history[0].focused_enrichment_applied
    assert history[0].pre_enrichment_evaluated_claims
    assert any(
        ev.label == KgcClaimLabel.NO_EVIDENCE
        for ev in history[0].pre_enrichment_evaluated_claims
    )
    assert history[0].supported_count >= 1
    assert stop_reason == SubQuestionStopReason.RESOLVED


def test_claim_moves_no_evidence_to_supported_without_changing_answer():
    provider = MockProvider()
    working_state = WorkingKgcState(
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    engine = KgcIterationEngine(
        provider,
        focused_extractor=_StubFocusedExtractor(),
    )
    answer = "Launched from Kennedy Space Center in Florida."
    final_answer, history, _, _ = engine.run_sub_question(
        question="Where was Apollo 11 launched from?",
        trusted_context=_example("apollo_complex").context,
        working_state=working_state,
        sub_question_id=3,
        initial_answer=answer,
        max_iterations=1,
    )
    assert final_answer == answer
    assert history[0].no_evidence_count == 0
    assert history[0].supported_count == 1


def test_apollo_complex_launch_location_regression():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
    )
    result = runner.run_example(_example("apollo_complex"))
    launch = next(
        r
        for r in result.sub_question_results
        if "launch" in r.question.lower()
    )
    assert "airport" in launch.initial_answer.lower()
    assert launch.final_supported >= 1
    assert any(
        f.relation == "launched_from" and "kennedy" in f.object.lower()
        for f in result.working_kgc_facts
    )


def test_sub_question_answer_generation_is_concise():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=1,
        answer_0_mode="context_grounded_per_subquestion",
    )
    result = runner.run_example(_example("apollo_complex"))
    lunar = next(
        r
        for r in result.sub_question_results
        if "lunar material" in r.question.lower()
    )
    assert "21.5 kg" in lunar.initial_answer
    assert "walking" not in lunar.initial_answer.lower()
    assert "telephone" not in lunar.initial_answer.lower()


def test_cumulative_vs_final_metrics_semantics():
    provider = MockProvider()
    working_state = WorkingKgcState(
        [KgcFact("Apollo 11", "launched_by", "Saturn V")],
    )
    engine = KgcIterationEngine(
        provider,
        focused_extractor=_StubFocusedExtractor(),
    )
    _, history, _, _ = engine.run_sub_question(
        question="Where was Apollo 11 launched from?",
        trusted_context=_example("apollo_complex").context,
        working_state=working_state,
        sub_question_id=3,
        initial_answer="Launched from Kennedy Space Center in Florida.",
        max_iterations=1,
    )
    cumulative_supported, _, cumulative_no_evidence = count_cumulative_evaluations(
        history
    )
    final_supported = history[-1].supported_count
    final_no_evidence = history[-1].no_evidence_count
    assert cumulative_no_evidence >= final_no_evidence
    assert cumulative_supported >= final_supported
    assert cumulative_no_evidence > 0
    assert final_no_evidence == 0


def test_decomposed_metrics_expose_cumulative_and_final_counts():
    runner = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=2,
    )
    result = runner.run_example(_example("apollo_complex"))
    metrics = result.metrics
    assert metrics is not None
    assert metrics.cumulative_supported_evaluations >= metrics.final_supported
    assert metrics.to_dict()["total_supported"] == metrics.cumulative_supported_evaluations
