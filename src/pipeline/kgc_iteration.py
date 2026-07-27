"""Shared helpers for KGc iteration loops."""

from __future__ import annotations

from src.models import (
    KgcClaimLabel,
    KgcEvaluationResult,
    KgcFact,
    SubQuestionIteration,
    SubQuestionStopReason,
)
from src.pipeline.backtracking_feedback_builder import BacktrackingFeedbackBuilder
from src.pipeline.backtracking_reviser import BacktrackingReviser
from src.pipeline.backtracking_runner import _enrich_evaluations
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_matching import normalize, normalize_entity_text, normalize_relation
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.kgc_serializer import serialize_kgc_facts
from src.pipeline.abstention_detection import is_abstention_answer
from src.pipeline.relevant_context_fact_extractor import RelevantContextFactExtractor
from src.pipeline.evidence_path_resolver import resolve_evidence_path
from src.pipeline.question_target import (
    derive_question_target,
    evaluate_target_satisfaction,
)
from src.pipeline.target_fact_deriver import (
    TargetFactDeriver,
    has_on_target_evaluation_facts,
)
from src.pipeline.target_frame_normalizer import TargetFrameTrace
from src.pipeline.triple_extractor import TripleExtractor
from src.pipeline.working_kgc import WorkingKgcState


def count_labels(evaluated_claims: list[KgcEvaluationResult]) -> tuple[int, int, int]:
    supported = sum(
        1 for ev in evaluated_claims if ev.label == KgcClaimLabel.SUPPORTED
    )
    contradicted = sum(
        1 for ev in evaluated_claims if ev.label == KgcClaimLabel.CONTRADICTED
    )
    no_evidence = sum(
        1 for ev in evaluated_claims if ev.label == KgcClaimLabel.NO_EVIDENCE
    )
    return supported, contradicted, no_evidence


def count_cumulative_evaluations(
    history: list[SubQuestionIteration],
) -> tuple[int, int, int]:
    supported = contradicted = no_evidence = 0
    for item in history:
        eval_sets: list[list[KgcEvaluationResult]] = [item.evaluated_claims]
        if item.pre_enrichment_evaluated_claims:
            eval_sets.insert(0, item.pre_enrichment_evaluated_claims)
        for evals in eval_sets:
            s, c, n = count_labels(evals)
            supported += s
            contradicted += c
            no_evidence += n
    return supported, contradicted, no_evidence


def evaluation_signature(evaluated_claims: list[KgcEvaluationResult]) -> str:
    parts = sorted(
        f"{ev.label.value}|{normalize(ev.triple.subject)}|"
        f"{normalize_relation(ev.triple.relation)}|{normalize(ev.triple.object)}"
        for ev in evaluated_claims
    )
    return ";".join(parts)


def normalize_answer_text(text: str) -> str:
    return normalize_entity_text(" ".join((text or "").strip().split()))


def determine_stop_reason(
    *,
    iteration: int,
    max_iterations: int,
    current_answer: str,
    previous_answer: str | None,
    previous_signature: str | None,
    current_signature: str,
    supported_count: int,
    contradicted_count: int,
    no_evidence_count: int,
    claim_count: int,
    target_satisfied: bool = True,
    supported_but_irrelevant_count: int = 0,
    answer_is_abstention: bool = False,
    focused_enrichment_attempted: bool = False,
    derivation_attempted: bool = False,
    evidence_path_complete: bool | None = None,
    new_facts_added: bool = False,
) -> tuple[SubQuestionStopReason | None, str | None]:
    answer_unchanged = (
        previous_answer is not None
        and normalize_answer_text(current_answer) == normalize_answer_text(previous_answer)
    )
    claims_unchanged = bool(
        previous_signature and previous_signature == current_signature
    )

    if claim_count == 0:
        if is_abstention_answer(current_answer):
            if previous_answer is not None and is_abstention_answer(previous_answer):
                return SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE, "repeated_abstention"
            if iteration > 0:
                return SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE, "abstention_after_revision"
            if focused_enrichment_attempted and iteration + 1 >= max_iterations:
                return SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE, "abstention_after_enrichment"
            if derivation_attempted and iteration + 1 >= max_iterations:
                return SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE, "abstention_after_derivation"
            if iteration == 0 and previous_answer is None:
                return SubQuestionStopReason.GENERATION_FAILED, "initial_abstention"
            if iteration + 1 >= max_iterations:
                return SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE, "abstention_max_iterations"
            return None, None
        if iteration + 1 >= max_iterations or iteration > 0:
            return SubQuestionStopReason.NO_CLAIMS_EXTRACTED, None
        return None, None

    if contradicted_count == 0 and no_evidence_count == 0 and claim_count > 0:
        if target_satisfied and evidence_path_complete is False:
            # Correct terminal text with a disconnected/incomplete path must not
            # resolve. Keep iterating when budget remains; otherwise leave as
            # target-unsatisfied so the defect is visible.
            if iteration + 1 >= max_iterations:
                return SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED, "incomplete_evidence_path"
            if (
                previous_answer is not None
                and answer_unchanged
                and claims_unchanged
                and not new_facts_added
            ):
                return (
                    SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
                    "unchanged_incomplete_evidence_path",
                )
            return None, "incomplete_evidence_path"
        if target_satisfied and evidence_path_complete is not False:
            return SubQuestionStopReason.RESOLVED, None
        if supported_but_irrelevant_count > 0 or supported_count > 0:
            # Supported claims with an unsatisfied target: do not keep revising
            # when the answer/claims are unchanged and no new trusted FACTS arrived.
            if (
                previous_answer is not None
                and (answer_unchanged or claims_unchanged)
                and not new_facts_added
            ):
                return (
                    SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
                    "unchanged_supported_target_unsatisfied",
                )
            if iteration + 1 >= max_iterations:
                return SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED, None
            return None, None

    if previous_answer is not None and not new_facts_added:
        if answer_unchanged:
            if (
                supported_but_irrelevant_count > 0
                and contradicted_count == 0
                and no_evidence_count == 0
            ):
                return SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED, None
            return SubQuestionStopReason.STALLED, None
        if claims_unchanged:
            if (
                supported_but_irrelevant_count > 0
                and contradicted_count == 0
                and no_evidence_count == 0
            ):
                return SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED, None
            return SubQuestionStopReason.STALLED, None

    if iteration + 1 >= max_iterations:
        if contradicted_count == 0 and no_evidence_count > 0:
            return SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE, None
        if supported_but_irrelevant_count > 0 and not target_satisfied:
            return SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED, None
        return SubQuestionStopReason.MAX_ITERATIONS, None

    if contradicted_count == 0 and no_evidence_count > 0:
        return None, None

    if contradicted_count > 0:
        return None, None

    return None, None


class KgcIterationEngine:
    """Runs extract → align → compare → feedback → revise for one sub-question."""

    def __init__(
        self,
        provider,
        *,
        claim_extractor: TripleExtractor | None = None,
        comparator: GraphComparator | None = None,
        feedback_builder: BacktrackingFeedbackBuilder | None = None,
        reviser: BacktrackingReviser | None = None,
        focused_extractor: RelevantContextFactExtractor | None = None,
    ) -> None:
        self._claim_extractor = claim_extractor or TripleExtractor(provider)
        self._comparator = comparator or GraphComparator()
        self._feedback_builder = feedback_builder or BacktrackingFeedbackBuilder()
        self._reviser = reviser or BacktrackingReviser(provider)
        self._focused_extractor = focused_extractor
        self._target_deriver = TargetFactDeriver()

    def run_sub_question(
        self,
        *,
        question: str,
        trusted_context: str,
        working_state: WorkingKgcState,
        sub_question_id: int,
        initial_answer: str,
        max_iterations: int,
        focused_extractor: RelevantContextFactExtractor | None = None,
        proactive_focused_enrichment_done: bool = False,
    ) -> tuple[str, list[SubQuestionIteration], SubQuestionStopReason, int]:
        extractor = focused_extractor or self._focused_extractor
        current_answer = initial_answer
        history: list[SubQuestionIteration] = []
        previous_answer: str | None = None
        previous_signature: str | None = None
        stop_reason = SubQuestionStopReason.MAX_ITERATIONS
        enrichment_retries = 0
        supported = contradicted = no_evidence = 0
        question_target = derive_question_target(
            question,
            working_state.facts_for_comparison(),
            trusted_context=trusted_context,
        )

        for iteration in range(max_iterations):
            kgc_facts = working_state.facts_for_comparison()
            serialized_kgc = serialize_kgc_facts(kgc_facts)
            frame_trace = TargetFrameTrace()
            answer_is_abstention = is_abstention_answer(current_answer)
            focused_raw_facts: list = []
            focused_filtered_facts: list = []
            derived_facts_added: list[KgcFact] = []
            derivation_trace_dict: dict | None = None
            derivation_attempted = False

            if answer_is_abstention:
                extracted_claims = []
                aligned_claims = []
                evaluated_claims = []
                pre_enrichment_evaluated = []
                focused_facts_added = []
                focused_enrichment_applied = False
                supported = contradicted = no_evidence = 0
            else:
                extracted_claims, aligned_claims = self._claim_extractor.extract_kgc_claims(
                    current_answer,
                    kgc_facts=kgc_facts,
                    question=question,
                    trusted_context=trusted_context,
                )
                from src.pipeline.debug_log import log_debug_event
                from src.pipeline.structured_output import get_last_parse_anomalies

                for anomaly in get_last_parse_anomalies():
                    log_debug_event(
                        "structured_triple_anomaly",
                        anomaly.reason,
                        anomaly.to_dict(),
                        sub_question_id=sub_question_id,
                    )

                aligned_claims, _alignment_traces = align_claims_to_kgc_schema(
                    aligned_claims,
                    kgc_facts,
                    question_target=question_target,
                )
                log_debug_event(
                    "claim_alignment",
                    "aligned",
                    {
                        "extracted": [
                            {
                                "subject": c.subject,
                                "relation": c.relation,
                                "object": c.object,
                            }
                            for c in extracted_claims
                        ],
                        "aligned": [
                            {
                                "subject": c.subject,
                                "relation": c.relation,
                                "object": c.object,
                            }
                            for c in aligned_claims
                        ],
                        "comparator_fact_count": len(kgc_facts),
                        "comparator_facts": [
                            {
                                "subject": f.subject,
                                "relation": f.relation,
                                "object": f.object,
                            }
                            for f in kgc_facts
                        ],
                    },
                    sub_question_id=sub_question_id,
                )
                evaluated_claims = self._comparator.compare_claims(
                    aligned_claims,
                    kgc_facts,
                    question_target=question_target,
                    question=question,
                    frame_trace=frame_trace,
                )
                log_debug_event(
                    "claim_comparison",
                    "compared",
                    {
                        "evaluations": [
                            {
                                "subject": ev.triple.subject,
                                "relation": ev.triple.relation,
                                "object": ev.triple.object,
                                "label": ev.label.value
                                if hasattr(ev.label, "value")
                                else str(ev.label),
                                "reason": ev.reason,
                            }
                            for ev in evaluated_claims
                        ]
                    },
                    sub_question_id=sub_question_id,
                )
                _enrich_evaluations(
                    extracted_claims,
                    aligned_claims,
                    current_answer,
                    evaluated_claims,
                )

                pre_enrichment_evaluated = []
                focused_facts_added = []
                focused_enrichment_applied = False

                supported, contradicted, no_evidence = count_labels(evaluated_claims)
                needs_enrichment = no_evidence > 0 or not has_on_target_evaluation_facts(
                    kgc_facts,
                    question_target,
                    question,
                )

                if needs_enrichment and extractor is not None:
                    if no_evidence > 0:
                        pre_enrichment_evaluated = list(evaluated_claims)
                    focused_facts, focus_trace = extractor.extract_with_trace(
                        question,
                        trusted_context,
                        existing_kgc_facts=kgc_facts,
                    )
                    focused_raw_facts = list(
                        getattr(focus_trace, "raw_focused_facts", focused_facts)
                    )
                    focused_filtered_facts = list(
                        getattr(focus_trace, "filtered_focused_facts", focused_facts)
                    )
                    enrichment_retries += getattr(focus_trace, "retry_count", 0)
                    added = working_state.merge_focused_facts(
                        focused_facts,
                        sub_question_id=sub_question_id,
                    )
                    if added:
                        focused_enrichment_applied = True
                        focused_facts_added = added
                        kgc_facts = working_state.facts_for_comparison()

                if not has_on_target_evaluation_facts(
                    kgc_facts,
                    question_target,
                    question,
                ):
                    derivation_attempted = True
                    derived, derivation_trace = self._target_deriver.derive(
                        question=question,
                        trusted_context=trusted_context,
                        target=question_target,
                        kgc_facts=kgc_facts,
                    )
                    derivation_trace_dict = derivation_trace.to_dict()
                    if derived:
                        first = derivation_trace.accepted[0] if derivation_trace.accepted else None
                        added_derived = working_state.merge_derived_facts(
                            derived,
                            sub_question_id=sub_question_id,
                            derivation_type=first.derivation_type if first else "target_derivation",
                            evidence_spans=first.evidence_spans if first else [],
                            derivation_explanation=first.explanation if first else None,
                        )
                        if added_derived:
                            derived_facts_added = added_derived
                            kgc_facts = working_state.facts_for_comparison()

                if focused_enrichment_applied or derived_facts_added:
                    serialized_kgc = serialize_kgc_facts(kgc_facts)
                    aligned_claims, _alignment_traces = align_claims_to_kgc_schema(
                        extracted_claims,
                        kgc_facts,
                        question_target=question_target,
                    )
                    evaluated_claims = self._comparator.compare_claims(
                        aligned_claims,
                        kgc_facts,
                        question_target=question_target,
                        question=question,
                        frame_trace=frame_trace,
                    )
                    _enrich_evaluations(
                        extracted_claims,
                        aligned_claims,
                        current_answer,
                        evaluated_claims,
                    )
                    supported, contradicted, no_evidence = count_labels(evaluated_claims)

            target_eval = evaluate_target_satisfaction(
                evaluated_claims,
                question_target,
            )
            terminal_claim = _select_terminal_claim(evaluated_claims, aligned_claims)
            path_result = resolve_evidence_path(
                question=question,
                current_answer=current_answer,
                answer_claim=terminal_claim,
                question_target=question_target,
                trusted_facts=working_state.facts_for_comparison(),
            )
            feedback = self._feedback_builder.build(evaluated_claims)
            feedback.extend(
                self._feedback_builder.build_target_adequacy_feedback(
                    evaluated_claims,
                    question_target,
                )
            )
            sig = evaluation_signature(evaluated_claims)

            pre_no_evidence = (
                count_labels(pre_enrichment_evaluated)[2] if pre_enrichment_evaluated else 0
            )
            focused_enrichment_attempted = (
                proactive_focused_enrichment_done
                or focused_enrichment_applied
                or derivation_attempted
                or any(h.focused_enrichment_applied for h in history)
                or any(h.derived_facts_added for h in history)
            )

            stop, abstention_stop_reason = determine_stop_reason(
                iteration=iteration,
                max_iterations=max_iterations,
                current_answer=current_answer,
                previous_answer=previous_answer,
                previous_signature=previous_signature,
                current_signature=sig,
                supported_count=supported,
                contradicted_count=contradicted,
                no_evidence_count=no_evidence,
                claim_count=len(evaluated_claims),
                target_satisfied=target_eval.satisfied,
                supported_but_irrelevant_count=target_eval.supported_but_irrelevant_count,
                answer_is_abstention=answer_is_abstention,
                focused_enrichment_attempted=focused_enrichment_attempted,
                derivation_attempted=derivation_attempted,
                evidence_path_complete=path_result.complete,
                new_facts_added=bool(focused_facts_added or derived_facts_added),
            )

            history.append(
                SubQuestionIteration(
                    iteration=iteration,
                    answer=current_answer,
                    extracted_claims=extracted_claims,
                    aligned_claims=aligned_claims,
                    evaluated_claims=evaluated_claims,
                    pre_enrichment_evaluated_claims=pre_enrichment_evaluated,
                    backtracking_feedback=feedback,
                    supported_count=supported,
                    contradicted_count=contradicted,
                    no_evidence_count=no_evidence,
                    evaluation_signature=sig,
                    focused_enrichment_applied=focused_enrichment_applied,
                    focused_facts_added=focused_facts_added,
                    question_target=question_target.to_dict(),
                    target_satisfied=target_eval.satisfied,
                    on_target_supported_count=target_eval.on_target_supported_count,
                    supported_but_irrelevant_count=target_eval.supported_but_irrelevant_count,
                    unsupported_target_count=target_eval.unsupported_target_count,
                    answer_is_abstention=answer_is_abstention,
                    pre_enrichment_no_evidence_count=pre_no_evidence,
                    target_frame_trace=frame_trace.to_dict(),
                    abstention_stop_reason=abstention_stop_reason,
                    focused_extraction_raw=focused_raw_facts,
                    focused_extraction_filtered=focused_filtered_facts,
                    derived_facts_added=derived_facts_added,
                    derivation_trace=derivation_trace_dict,
                    evidence_path=path_result.to_dict(),
                    evidence_path_complete=path_result.complete,
                    evidence_path_length=path_result.path_length,
                )
            )

            if stop is not None:
                stop_reason = stop
                break

            answer_next = self._reviser.revise(
                question,
                serialized_kgc,
                current_answer,
                feedback,
            )
            previous_answer = current_answer
            previous_signature = sig
            current_answer = answer_next
        else:
            # for/else: the loop completed without an early stop. Use the final
            # iteration's label counts — the loop-local names contradicted_count /
            # no_evidence_count are not in scope here on every path.
            last_item = history[-1] if history else None
            last_evals = last_item.evaluated_claims if last_item else []
            last_supported, last_contradicted, last_no_evidence = count_labels(last_evals)
            last_target = evaluate_target_satisfaction(last_evals, question_target)
            if (
                not last_target.satisfied
                and last_target.supported_but_irrelevant_count > 0
                and last_contradicted == 0
                and last_no_evidence == 0
            ):
                stop_reason = SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED
            elif last_contradicted == 0 and last_no_evidence > 0:
                stop_reason = SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE
            elif (
                last_contradicted == 0
                and last_no_evidence == 0
                and last_supported > 0
                and last_target.satisfied
            ):
                stop_reason = SubQuestionStopReason.RESOLVED
            else:
                stop_reason = SubQuestionStopReason.MAX_ITERATIONS

        return current_answer, history, stop_reason, enrichment_retries


def _select_terminal_claim(
    evaluated_claims: list[KgcEvaluationResult],
    aligned_claims: list,
):
    """Prefer the trusted FACT matched by a supported claim; else the claim itself.

    Comparator support can accept compatible object phrasings that are not
    character-identical to the stored FACT. The evidence path must walk trusted
    FACT edges, so the matched KGc fact is the terminal edge when present.
    """
    from src.models import Triple

    for evaluation in evaluated_claims:
        if evaluation.label == KgcClaimLabel.SUPPORTED:
            matched = evaluation.matched_kgc_fact
            if matched is not None:
                return Triple(
                    subject=matched.subject,
                    relation=matched.relation,
                    object=matched.object,
                    source_sentence=evaluation.triple.source_sentence,
                )
            return evaluation.triple
    if aligned_claims:
        return aligned_claims[0]
    if evaluated_claims:
        return evaluated_claims[0].triple
    return None
