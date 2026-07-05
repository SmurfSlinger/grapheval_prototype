"""Build backtracking feedback from KGc evaluation results."""

from __future__ import annotations

from src.models import BacktrackingFeedbackItem, KgcClaimLabel, KgcEvaluationResult


def backtracking_action_for_label(label: KgcClaimLabel) -> str:
    if label == KgcClaimLabel.SUPPORTED:
        return "Preserve this supported claim in Answer(n+1)."
    if label == KgcClaimLabel.CONTRADICTED:
        return "Correct or remove this claim using the conflicting KGc fact."
    return (
        "Omit this unsupported claim from Answer(n+1) or mark it for "
        "retrieval/adjudication."
    )


class BacktrackingFeedbackBuilder:
    def build(
        self,
        evaluations: list[KgcEvaluationResult],
    ) -> list[BacktrackingFeedbackItem]:
        feedback: list[BacktrackingFeedbackItem] = []
        for ev in evaluations:
            action = ev.backtracking_action or backtracking_action_for_label(ev.label)
            if ev.label == KgcClaimLabel.SUPPORTED:
                instruction = "Preserve this claim; it is supported by KGc."
            elif ev.label == KgcClaimLabel.CONTRADICTED:
                instruction = (
                    f"Answer claimed '{ev.triple.object}', but KGc says "
                    f"'{ev.conflicting_object}'; correct or remove using KGc."
                )
            else:
                instruction = (
                    "KGc does not support this claim; omit it from the corrected "
                    "answer or mark it for later retrieval/adjudication."
                )

            feedback.append(
                BacktrackingFeedbackItem(
                    triple=ev.triple,
                    label=ev.label,
                    instruction=instruction,
                    reason=ev.reason,
                    evidence=ev.evidence,
                    conflicting_object=ev.conflicting_object,
                    matched_kgc_fact=ev.matched_kgc_fact,
                    conflicting_fact=ev.conflicting_fact,
                    backtracking_action=action,
                )
            )
        return feedback
