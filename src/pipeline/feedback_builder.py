"""Build revision instructions from failed verification results."""

from __future__ import annotations

from src.models import FeedbackItem, VerificationLabel, VerificationResult


class FeedbackBuilder:
    """Turn verification failures into structured feedback for revision."""

    def build(self, verification_results: list[VerificationResult]) -> list[FeedbackItem]:
        feedback: list[FeedbackItem] = []
        for result in verification_results:
            if result.label == VerificationLabel.SUPPORTED:
                continue
            instruction = self._instruction_for(result.label, result.triple)
            feedback.append(
                FeedbackItem(
                    triple=result.triple,
                    status=result.label,
                    instruction=instruction,
                    evidence=result.evidence,
                )
            )
        return feedback

    @staticmethod
    def _instruction_for(label: VerificationLabel, triple) -> str:
        claim = f"({triple.subject}, {triple.relation}, {triple.object})"
        if label == VerificationLabel.CONTRADICTED:
            return f"Remove or correct the contradicted claim: {claim}"
        return f"Revise or remove the unsupported claim: {claim}"
