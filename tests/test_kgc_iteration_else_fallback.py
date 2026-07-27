"""Regression: the for/else fallback of run_sub_question must not NameError."""

from __future__ import annotations

from src.llm.mock_provider import MockProvider
from src.models import KgcClaimLabel, KgcEvaluationResult, KgcFact, SubQuestionStopReason, Triple
from src.pipeline.kgc_iteration import KgcIterationEngine
from src.pipeline.working_kgc import WorkingKgcState


class _StaticClaimExtractor:
    def extract_kgc_claims(self, answer, *, kgc_facts=None, question=None, trusted_context=None):
        claim = Triple("Apollo 11", "occurred_during", "July 1969")
        return [claim], [claim]


class _StaticComparator:
    def compare_claims(self, claims, kgc_facts, **kwargs):
        return [
            KgcEvaluationResult(
                triple=claim,
                label=KgcClaimLabel.NO_EVIDENCE,
                reason="forced",
                evidence="",
            )
            for claim in claims
        ]


class _StaticFeedback:
    def build(self, evaluations):
        return []

    def build_target_adequacy_feedback(self, evaluations, target):
        return []


class _StaticReviser:
    def __init__(self):
        self.provider = MockProvider()

    def revise(self, question, serialized_kgc, answer, feedback):
        return answer + " revised"


def test_run_sub_question_for_else_fallback_does_not_nameerror(monkeypatch):
    """Force every iteration to continue so the loop else path executes."""
    import src.pipeline.kgc_iteration as iteration_module

    monkeypatch.setattr(
        iteration_module,
        "determine_stop_reason",
        lambda **kwargs: (None, None),
    )

    engine = KgcIterationEngine(
        MockProvider(),
        claim_extractor=_StaticClaimExtractor(),
        comparator=_StaticComparator(),
        feedback_builder=_StaticFeedback(),
        reviser=_StaticReviser(),
        focused_extractor=None,
    )
    working = WorkingKgcState(
        [KgcFact("Apollo 11", "launched_from", "Kennedy Space Center")]
    )

    answer, history, stop_reason, _retries = engine.run_sub_question(
        question="When was the Apollo 11 mission?",
        trusted_context="Apollo 11 occurred during July 16-24, 1969.",
        working_state=working,
        sub_question_id=1,
        initial_answer="July 1969",
        max_iterations=2,
        focused_extractor=None,
        proactive_focused_enrichment_done=True,
    )

    assert history
    assert len(history) == 2
    assert stop_reason in {
        SubQuestionStopReason.MAX_ITERATIONS,
        SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE,
        SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
        SubQuestionStopReason.RESOLVED,
    }
    assert isinstance(answer, str)
