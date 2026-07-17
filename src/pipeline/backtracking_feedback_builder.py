"""Build backtracking feedback from KGc evaluation results."""

from __future__ import annotations

from src.models import BacktrackingFeedbackItem, KgcClaimLabel, KgcEvaluationResult
from src.pipeline.question_target import QuestionTarget, relation_matches_target


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
                instruction = (
                    "Preserve this claim component; it is supported by KGc. "
                    "Do not replace correct attributes while correcting others."
                )
            elif ev.label == KgcClaimLabel.CONTRADICTED:
                instruction = (
                    f"Answer claimed '{ev.triple.object}', but KGc says "
                    f"'{ev.conflicting_object}'. Correct only this contradicted "
                    "attribute; preserve any sibling supported claim components "
                    "in the same answer fragment."
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

    def build_target_adequacy_feedback(
        self,
        evaluations: list[KgcEvaluationResult],
        target: QuestionTarget,
    ) -> list[BacktrackingFeedbackItem]:
        if not target.expected_relations:
            return []

        feedback: list[BacktrackingFeedbackItem] = []
        for ev in evaluations:
            if ev.label != KgcClaimLabel.SUPPORTED:
                continue
            if relation_matches_target(ev.triple.relation, target):
                continue
            feedback.append(
                BacktrackingFeedbackItem(
                    triple=ev.triple,
                    label=ev.label,
                    instruction=(
                        f"Claim uses relation '{ev.triple.relation}', but the sub-question "
                        f"requires {target.intent.replace('_', ' ')} "
                        f"({', '.join(sorted(target.expected_relations))}). "
                        "Provide an answer claim that directly addresses the sub-question."
                    ),
                    reason=(
                        "Supported claim does not satisfy the sub-question target relation."
                    ),
                    evidence=ev.evidence,
                    matched_kgc_fact=ev.matched_kgc_fact,
                    backtracking_action=(
                        "Replace this supported but off-target claim with one that "
                        "answers the sub-question."
                    ),
                )
            )
        return feedback
