"""Unit tests for backtracking feedback builder."""

from src.models import KgcClaimLabel, KgcEvaluationResult, KgcFact, Triple
from src.pipeline.backtracking_feedback_builder import BacktrackingFeedbackBuilder

HYUNDAI = "2018 Hyundai Sonata SE"


def _evaluation(label: KgcClaimLabel, relation: str, obj: str) -> KgcEvaluationResult:
    conflicting_fact = None
    conflicting_object = None
    if label == KgcClaimLabel.CONTRADICTED:
        conflicting_object = "Alabama"
        conflicting_fact = KgcFact(
            subject=HYUNDAI,
            relation="assembled_in",
            object="Alabama",
        )
    return KgcEvaluationResult(
        triple=Triple(subject=HYUNDAI, relation=relation, object=obj),
        label=label,
        reason=f"Test reason for {label.value}.",
        evidence="Test evidence.",
        conflicting_object=conflicting_object,
        conflicting_fact=conflicting_fact,
    )


def test_backtracking_feedback_preserves_supported_claims():
    """SUPPORTED evaluations should instruct the reviser to preserve the claim."""
    feedback = BacktrackingFeedbackBuilder().build(
        [_evaluation(KgcClaimLabel.SUPPORTED, "has_engine", "2.4L engine")]
    )

    assert len(feedback) == 1
    assert "preserve" in feedback[0].instruction.lower(), (
        "Supported claim feedback should say to preserve the claim"
    )


def test_backtracking_feedback_corrects_contradicted_claims():
    """CONTRADICTED evaluations should reference the conflicting KGc object."""
    feedback = BacktrackingFeedbackBuilder().build(
        [_evaluation(KgcClaimLabel.CONTRADICTED, "assembled_in", "Korea")]
    )

    assert len(feedback) == 1
    assert feedback[0].conflicting_object == "Alabama", (
        "Contradicted feedback should carry the conflicting KGc object"
    )
    assert "Alabama" in feedback[0].instruction, (
        "Contradicted feedback should mention the KGc object to use instead"
    )
    assert "kgc" in feedback[0].instruction.lower(), (
        "Contradicted feedback should direct correction using KGc"
    )


def test_backtracking_feedback_flags_no_evidence_claims():
    """NO_EVIDENCE evaluations should instruct omitting or deferring the claim."""
    feedback = BacktrackingFeedbackBuilder().build(
        [_evaluation(KgcClaimLabel.NO_EVIDENCE, "has_turbo", "true")]
    )

    assert len(feedback) == 1
    instruction = feedback[0].instruction.lower()
    assert (
        "omit" in instruction
        or "retrieval" in instruction
        or "adjudication" in instruction
    ), "No-evidence feedback should say to omit or defer the unsupported claim"
