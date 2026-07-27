"""Decomposed iterative KGc backtracking for compound questions."""

from __future__ import annotations

from typing import Literal

from src.llm.base import LLMProvider
from src.models import (
    DecomposedBacktrackingResult,
    DecomposedBacktrackingTrace,
    DecomposedExperimentMetrics,
    Example,
    KgcClaimLabel,
    SubQuestion,
    SubQuestionResult,
    SubQuestionStopReason,
)
from src.pipeline.answer_generator import AnswerGenerator
from src.pipeline.context_triple_extractor import ContextTripleExtractor
from src.pipeline.debug_log import (
    begin_debug_run,
    current_debug_log_path,
    end_debug_run,
    log_debug_event,
    set_debug_context,
)
from src.pipeline.execution_context import ExecutionScope
from src.pipeline.kgc_iteration import KgcIterationEngine, count_cumulative_evaluations
from src.pipeline.kgc_serializer import serialize_kgc_facts
from src.pipeline.provider_info import provider_label, provider_model, provider_trace
from src.pipeline.question_splitter import QuestionSplitter
from src.pipeline.relevant_context_fact_extractor import RelevantContextFactExtractor
from src.pipeline.structured_output import (
    begin_anomaly_collection,
    end_anomaly_collection,
    get_run_parse_anomalies,
)
from src.pipeline.sub_answer_combiner import combine_sub_answers
from src.pipeline.sub_answer_projector import SubAnswerProjector
from src.pipeline.working_kgc import WorkingKgcState
from src.config import NEO4J_ENABLED
from src.storage.neo4j_store import (
    clear_execution_if_enabled,
    read_kgc_facts_if_enabled,
    store_kgc_claims_if_enabled,
    store_kgc_facts_if_enabled,
    store_working_kgc_additions_if_enabled,
)

DecomposedAnswer0Mode = Literal[
    "preset_external_projected",
    "generated_external_projected",
    "context_grounded_per_subquestion",
]


def resolve_decomposed_answer_0_mode(
    example: Example,
    answer_0_mode: str,
) -> tuple[DecomposedAnswer0Mode, str | None]:
    if answer_0_mode == "context_grounded_per_subquestion":
        return "context_grounded_per_subquestion", None
    if answer_0_mode in ("generated", "generated_external_projected"):
        return "generated_external_projected", None
    if example.initial_answer:
        return "preset_external_projected", None
    return (
        "generated_external_projected",
        "Preset mode selected but no initial_answer exists; "
        "generating compound Answer(0) before projection.",
    )


class DecomposedBacktrackingRunner:
    """Experimental runner: split compound question → iterate per sub-question → combine."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        max_iterations_per_sub_question: int = 3,
        working_kgc_auto_promote: bool = False,
        answer_0_mode: str = "preset",
        clear_neo4j_before_run: bool = False,
        neo4j_readback: bool = False,
        require_neo4j: bool = False,
    ) -> None:
        self.provider = provider
        self.max_iterations_per_sub_question = max_iterations_per_sub_question
        self.working_kgc_auto_promote = working_kgc_auto_promote
        self.answer_0_mode = answer_0_mode
        self.clear_neo4j_before_run = clear_neo4j_before_run
        self.neo4j_readback = neo4j_readback
        self.require_neo4j = require_neo4j
        self._question_splitter = QuestionSplitter(provider)
        self._context_extractor = ContextTripleExtractor(provider)
        self._focused_extractor = RelevantContextFactExtractor(provider)
        self._answer_generator = AnswerGenerator(provider)
        self._projector = SubAnswerProjector(provider)
        self._iteration_engine = KgcIterationEngine(
            provider,
            focused_extractor=self._focused_extractor,
        )

    def run_example(
        self,
        example: Example,
        *,
        attempt: int | None = None,
        execution_id: str | None = None,
        benchmark_id: str | None = None,
        question_id: str | None = None,
    ) -> DecomposedBacktrackingResult:
        # One immutable execution identity per attempt, generated at the boundary.
        scope = ExecutionScope.begin(
            example.id,
            benchmark_id=benchmark_id,
            question_id=question_id,
            execution_id=execution_id,
        )
        begin_anomaly_collection()
        debug_log_path = begin_debug_run(
            example.id,
            attempt=attempt,
            execution_id=scope.execution_id,
        )
        anomalies: list[dict] = []
        set_debug_context(question_id=example.id, execution_id=scope.execution_id)
        log_debug_event(
            "request_received",
            "run_example_started",
            {
                "example_id": example.id,
                "execution_id": scope.execution_id,
                "benchmark_id": scope.benchmark_id,
                "benchmark_question_id": scope.question_id,
                "question": example.question,
                "context_chars": len(example.context or ""),
                "has_initial_answer": bool(example.initial_answer),
                "answer_0_mode": self.answer_0_mode,
                "neo4j_readback": self.neo4j_readback,
                "attempt": attempt,
            },
        )
        try:
            return self._run_example_inner(
                example,
                scope=scope,
                debug_log_path=debug_log_path,
                anomalies=anomalies,
            )
        except Exception as exc:
            log_debug_event(
                "run_error",
                type(exc).__name__,
                {"error": str(exc)},
            )
            raise
        finally:
            end_debug_run()
            end_anomaly_collection()

    def _run_example_inner(
        self,
        example: Example,
        *,
        scope: ExecutionScope,
        debug_log_path: str | None,
        anomalies: list[dict],
    ) -> DecomposedBacktrackingResult:
        provider_info = provider_trace(self.provider)
        # Execution-scoped: a fresh execution ID has nothing to clear, and other
        # executions' graph state is never touched. Full graph deletion is only
        # available through the explicit development reset helper.
        neo4j_cleared = clear_execution_if_enabled(
            scope.execution_id,
            required=self.clear_neo4j_before_run,
        ) if self.clear_neo4j_before_run else False
        effective_mode, answer_0_warning = resolve_decomposed_answer_0_mode(
            example,
            self.answer_0_mode,
        )
        stage_providers = {
            "question_splitter": provider_label(self._question_splitter.provider),
            "context_extractor": provider_label(self._context_extractor.provider),
            "focused_extractor": provider_label(self._focused_extractor.provider),
            "answer_generator": provider_label(self._answer_generator.provider),
            "sub_answer_projector": provider_label(self._projector.provider),
            "claim_extractor": provider_label(self._iteration_engine._claim_extractor.provider),
            "reviser": provider_label(self._iteration_engine._reviser.provider),
        }
        log_debug_event(
            "example_constructed",
            "ready",
            {
                "example_id": example.id,
                "effective_answer_0_mode": effective_mode,
                "stage_providers": stage_providers,
            },
        )

        sub_questions, split_retries = self._question_splitter.split(example.question)
        log_debug_event(
            "question_split_parsed",
            "parsed",
            {
                "sub_questions": [
                    {"id": sq.id, "question": sq.question} for sq in sub_questions
                ],
                "retries": split_retries,
            },
        )

        base_kgc_facts, kgc_trace = self._context_extractor.extract_with_trace(
            example.context
        )
        log_debug_event(
            "context_fact_parsed",
            "base_facts_ready",
            {
                "fact_count": len(base_kgc_facts),
                "facts": [
                    {
                        "subject": f.subject,
                        "relation": f.relation,
                        "object": f.object,
                    }
                    for f in base_kgc_facts
                ],
                "extraction_trace": kgc_trace.to_dict(),
            },
        )
        base_facts_persisted = store_kgc_facts_if_enabled(
            scope,
            base_kgc_facts,
            required=self.require_neo4j,
        )
        log_debug_event(
            "neo4j_fact_write",
            "base_facts",
            {
                "execution_id": scope.execution_id,
                "persisted": bool(base_facts_persisted),
                "fact_count": len(base_kgc_facts) if base_facts_persisted else 0,
            },
        )
        kgc_evaluation_source = "in_memory"
        if self.neo4j_readback:
            persisted_facts = read_kgc_facts_if_enabled(
                scope.execution_id,
                required=self.require_neo4j,
            )
            if persisted_facts is not None:
                if base_kgc_facts and not persisted_facts:
                    raise RuntimeError(
                        "Neo4j FACT readback returned no facts after context persistence."
                    )
                log_debug_event(
                    "neo4j_fact_readback",
                    "replaced_base_facts",
                    {
                        "readback_count": len(persisted_facts),
                        "facts": [
                            {
                                "subject": f.subject,
                                "relation": f.relation,
                                "object": f.object,
                            }
                            for f in persisted_facts
                        ],
                    },
                )
                base_kgc_facts = persisted_facts
                kgc_evaluation_source = "neo4j_readback"

        working_state = WorkingKgcState(
            base_kgc_facts,
            auto_promote=self.working_kgc_auto_promote,
        )
        log_debug_event(
            "working_kgc_initialized",
            "ready",
            {
                "working_fact_count": len(working_state.facts_for_comparison()),
                "auto_promote": self.working_kgc_auto_promote,
                "kgc_evaluation_source": kgc_evaluation_source,
            },
        )

        compound_answer_0 = ""
        compound_answer_0_source = ""
        projected_answers: dict[int, str] = {}
        projection_retries = 0
        projection_method: str | None = None
        projection_source: str | None = None
        projection_faithfulness_passed: bool | None = None

        if effective_mode == "context_grounded_per_subquestion":
            trace_answer_0_mode = "context_grounded_per_subquestion"
        else:
            if effective_mode == "preset_external_projected":
                compound_answer_0 = example.initial_answer or ""
                compound_answer_0_source = "example.initial_answer"
            else:
                compound_answer_0 = self._answer_generator.generate(
                    example.question,
                    example.context,
                )
                compound_answer_0_source = "generated_compound_answer_0"
            projections, projection_trace = self._projector.project(
                example.question,
                sub_questions,
                compound_answer_0,
            )
            projection_retries = projection_trace.retry_count
            projection_method = projection_trace.method
            projection_source = projection_trace.source
            projection_faithfulness_passed = projection_trace.faithfulness_passed
            projected_answers = {
                item.sub_question_id: item.answer for item in projections
            }
            trace_answer_0_mode = effective_mode

        resolved_carry_forward: list[tuple[int, str, str]] = []
        sub_results: list[SubQuestionResult] = []
        total_retries = split_retries + kgc_trace.retry_count + projection_retries
        metrics = DecomposedExperimentMetrics(
            sub_question_count=len(sub_questions),
            compound_answer_0=compound_answer_0,
        )

        for sub_question in sub_questions:
            set_debug_context(sub_question_id=sub_question.id)
            carry_forward = working_state.build_carry_forward_context(resolved_carry_forward)

            focused_facts, proactive_trace = self._focused_extractor.extract_with_trace(
                sub_question.question,
                example.context,
                existing_kgc_facts=working_state.facts_for_comparison(),
            )
            total_retries += proactive_trace.retry_count

            proactive_added = working_state.merge_focused_facts(
                focused_facts,
                sub_question_id=sub_question.id,
            )
            log_debug_event(
                "focused_fact_extraction",
                "merged",
                {
                    "raw_count": len(proactive_trace.raw_focused_facts),
                    "merged_count": len(proactive_added),
                    "facts": [
                        {
                            "subject": f.subject,
                            "relation": f.relation,
                            "object": f.object,
                        }
                        for f in proactive_added
                    ],
                },
                sub_question_id=sub_question.id,
            )

            if effective_mode == "context_grounded_per_subquestion":
                initial_answer = self._answer_generator.generate_sub_answer(
                    question=sub_question.question,
                    trusted_context=example.context,
                    carry_forward_context=carry_forward,
                    working_kgc=working_state.facts_for_comparison(),
                )
            else:
                initial_answer = projected_answers[sub_question.id]

            final_answer, history, stop_reason, enrichment_retries = (
                self._iteration_engine.run_sub_question(
                    question=sub_question.question,
                    trusted_context=example.context,
                    working_state=working_state,
                    sub_question_id=sub_question.id,
                    initial_answer=initial_answer,
                    max_iterations=self.max_iterations_per_sub_question,
                    focused_extractor=self._focused_extractor,
                    proactive_focused_enrichment_done=bool(proactive_added),
                )
            )
            total_retries += enrichment_retries

            reactive_added = sum(
                len(h.focused_facts_added)
                for h in history
                if h.focused_enrichment_applied
            )

            first_iter = history[0] if history else None
            last_iter = history[-1] if history else None
            initial_supported = first_iter.supported_count if first_iter else 0
            initial_contradicted = first_iter.contradicted_count if first_iter else 0
            initial_no_evidence = first_iter.no_evidence_count if first_iter else 0
            final_supported = last_iter.supported_count if last_iter else 0
            final_contradicted = last_iter.contradicted_count if last_iter else 0
            final_no_evidence = last_iter.no_evidence_count if last_iter else 0
            cumulative_supported, cumulative_contradicted, cumulative_no_evidence = (
                count_cumulative_evaluations(history)
            )
            revision_count = max(0, len(history) - 1)
            resolved_without_revision = (
                stop_reason == SubQuestionStopReason.RESOLVED and revision_count == 0
            )
            corrected_claims = 0
            if first_iter and last_iter and first_iter != last_iter:
                corrected_claims = sum(
                    1
                    for pre, post in zip(
                        first_iter.evaluated_claims,
                        last_iter.evaluated_claims,
                        strict=False,
                    )
                    if pre.label != KgcClaimLabel.SUPPORTED
                    and post.label == KgcClaimLabel.SUPPORTED
                )

            if last_iter:
                for ev in last_iter.evaluated_claims:
                    working_state.record_evaluation(
                        ev,
                        sub_question_id=sub_question.id,
                        iteration=last_iter.iteration,
                    )

            sub_result = SubQuestionResult(
                sub_question_id=sub_question.id,
                question=sub_question.question,
                initial_answer=initial_answer,
                final_answer=final_answer,
                stop_reason=stop_reason,
                iteration_count=len(history),
                iteration_history=history,
                supported_count=final_supported,
                contradicted_count=final_contradicted,
                no_evidence_count=final_no_evidence,
                final_supported=final_supported,
                final_contradicted=final_contradicted,
                final_no_evidence=final_no_evidence,
                cumulative_supported_evaluations=cumulative_supported,
                cumulative_contradicted_evaluations=cumulative_contradicted,
                cumulative_no_evidence_evaluations=cumulative_no_evidence,
                focused_facts_added_count=len(proactive_added) + reactive_added,
                proactive_focused_facts_added=len(proactive_added),
                reactive_focused_facts_added=reactive_added,
                working_kgc_count_after=len(working_state.working_kgc),
                initial_supported=initial_supported,
                initial_contradicted=initial_contradicted,
                initial_no_evidence=initial_no_evidence,
                revision_count=revision_count,
                resolved_without_revision=resolved_without_revision,
                question_target=last_iter.question_target if last_iter else None,
                question_target_satisfied=last_iter.target_satisfied if last_iter else False,
                supported_but_irrelevant_count=(
                    last_iter.supported_but_irrelevant_count if last_iter else 0
                ),
                unsupported_target_count=(
                    last_iter.unsupported_target_count if last_iter else 0
                ),
                focused_extraction_raw=list(proactive_trace.raw_focused_facts),
                focused_extraction_filtered=list(proactive_trace.filtered_focused_facts),
                focused_extraction_merged=list(proactive_added),
                evidence_path=last_iter.evidence_path if last_iter else None,
                evidence_path_complete=(
                    last_iter.evidence_path_complete if last_iter else False
                ),
                evidence_path_length=(
                    last_iter.evidence_path_length if last_iter else 0
                ),
            )
            sub_results.append(sub_result)
            log_debug_event(
                "sub_question_finished",
                stop_reason.value if hasattr(stop_reason, "value") else str(stop_reason),
                {
                    "final_answer": final_answer,
                    "iteration_count": len(history),
                    "final_supported": final_supported,
                    "final_contradicted": final_contradicted,
                    "final_no_evidence": final_no_evidence,
                    "claims": [
                        {
                            "subject": ev.triple.subject,
                            "relation": ev.triple.relation,
                            "object": ev.triple.object,
                            "label": ev.label.value
                            if hasattr(ev.label, "value")
                            else str(ev.label),
                        }
                        for ev in (last_iter.evaluated_claims if last_iter else [])
                    ],
                },
                sub_question_id=sub_question.id,
            )

            for item in history:
                store_kgc_claims_if_enabled(
                    scope,
                    iteration=item.iteration,
                    evaluations=item.evaluated_claims,
                    answer_stage=(
                        f"sub_question_{sub_question.id}_answer_{item.iteration}"
                    ),
                    sub_question_id=sub_question.id,
                    required=self.require_neo4j,
                )

            metrics.total_iterations += len(history)
            metrics.total_claims_extracted += sum(
                len(h.extracted_claims) for h in history
            )
            metrics.total_claims_evaluated += (
                cumulative_supported + cumulative_contradicted + cumulative_no_evidence
            )
            metrics.cumulative_supported_evaluations += cumulative_supported
            metrics.cumulative_contradicted_evaluations += cumulative_contradicted
            metrics.cumulative_no_evidence_evaluations += cumulative_no_evidence
            metrics.final_supported += final_supported
            metrics.final_contradicted += final_contradicted
            metrics.final_no_evidence += final_no_evidence
            metrics.total_initial_contradicted += initial_contradicted
            metrics.total_initial_no_evidence += initial_no_evidence
            metrics.total_revisions += revision_count
            metrics.corrected_claims_count += corrected_claims
            metrics.supported_but_irrelevant_count += sub_result.supported_but_irrelevant_count
            metrics.unsupported_target_count += sub_result.unsupported_target_count
            for h in history:
                metrics.pre_enrichment_no_evidence_events += h.pre_enrichment_no_evidence_count
                if h.focused_enrichment_applied:
                    metrics.post_enrichment_no_evidence_events += h.no_evidence_count
                trace = h.target_frame_trace or {}
                metrics.target_frame_normalizations += trace.get("target_frame_normalizations", 0)
                metrics.relation_family_matches += trace.get("relation_family_matches", 0)
                metrics.subject_alias_matches += trace.get("subject_alias_matches", 0)
                metrics.target_scoped_fact_projections += trace.get(
                    "target_scoped_fact_projections", 0
                )
            if stop_reason == SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE and any(
                h.answer_is_abstention for h in history
            ):
                metrics.abstention_stops += 1

            if stop_reason == SubQuestionStopReason.RESOLVED:
                metrics.resolved_sub_questions += 1
                if resolved_without_revision:
                    metrics.resolved_without_revision_count += 1
                else:
                    metrics.resolved_after_revision_count += 1
                resolved_carry_forward.append(
                    (sub_question.id, sub_question.question, final_answer)
                )
            elif stop_reason == SubQuestionStopReason.STALLED:
                metrics.stalled_sub_questions += 1
            elif stop_reason == SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE:
                metrics.unresolved_sub_questions += 1
            elif stop_reason == SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED:
                metrics.unresolved_sub_questions += 1
                metrics.unresolved_target_not_satisfied_count += 1
            elif stop_reason == SubQuestionStopReason.MAX_ITERATIONS:
                metrics.max_iterations_sub_questions += 1
            elif stop_reason == SubQuestionStopReason.GENERATION_FAILED:
                metrics.generation_failed_sub_questions += 1
            elif stop_reason == SubQuestionStopReason.NO_CLAIMS_EXTRACTED:
                metrics.no_claims_sub_questions += 1

        combined_answer = combine_sub_answers(sub_results)
        log_debug_event(
            "combined_answer",
            "produced",
            {"combined_answer": combined_answer},
        )
        metrics.structured_output_retries = total_retries
        working_facts_persisted = store_working_kgc_additions_if_enabled(
            scope,
            working_state.focused_additions,
            required=self.require_neo4j,
        )

        trace = DecomposedBacktrackingTrace(
            working_kgc_auto_promote=self.working_kgc_auto_promote,
            structured_output_retries=total_retries,
            answer_0_mode=trace_answer_0_mode,
            provider_class=provider_info["provider_class"],
            model=provider_model(self.provider),
            example_id=example.id,
            execution_id=scope.execution_id,
            benchmark_id=scope.benchmark_id,
            question_id=scope.question_id,
            context_extraction_format=kgc_trace.format_used,
            context_extraction_trace=kgc_trace.to_dict(),
            stage_providers=stage_providers,
            compound_answer_0_source=compound_answer_0_source or None,
            projection_trace_retries=projection_retries,
            projection_method=projection_method,
            projection_source=projection_source,
            projection_faithfulness_passed=projection_faithfulness_passed,
            configured_num_ctx=getattr(self.provider, "num_ctx", None),
            llm_call_telemetry=list(
                getattr(self.provider, "call_telemetry", [])
            ),
            neo4j_enabled=NEO4J_ENABLED,
            neo4j_cleared_before_run=neo4j_cleared,
            neo4j_base_facts_persisted=(
                len(base_kgc_facts) if base_facts_persisted else 0
            ),
            neo4j_working_facts_persisted=(
                len(working_state.focused_additions)
                if working_facts_persisted
                else 0
            ),
            kgc_evaluation_source=kgc_evaluation_source,
        )
        if answer_0_warning:
            trace.compound_answer_0_source = (
                f"{compound_answer_0_source}; warning={answer_0_warning}"
                if compound_answer_0_source
                else answer_0_warning
            )

        anomalies.extend(a.to_dict() for a in get_run_parse_anomalies())
        log_debug_event(
            "run_finished",
            "ok",
            {
                "execution_id": scope.execution_id,
                "combined_answer": combined_answer,
                "anomaly_count": len(anomalies),
                "base_fact_count": len(base_kgc_facts),
                "working_fact_count": len(working_state.working_kgc),
                "debug_log_path": debug_log_path or current_debug_log_path(),
            },
        )
        return DecomposedBacktrackingResult(
            example_id=example.id,
            execution_id=scope.execution_id,
            original_question=example.question,
            context=example.context,
            sub_questions=sub_questions,
            sub_question_results=sub_results,
            combined_answer=combined_answer,
            base_kgc_facts=base_kgc_facts,
            working_kgc_facts=working_state.working_kgc,
            working_kgc_additions=working_state.focused_additions,
            candidate_kgc_updates=working_state.candidate_updates,
            trace=trace,
            debug_log_path=debug_log_path or current_debug_log_path(),
            structured_triple_anomalies=list(anomalies),
            metrics=metrics,
            carry_forward_context=working_state.build_carry_forward_context(
                resolved_carry_forward
            ),
            max_iterations_per_sub_question=self.max_iterations_per_sub_question,
        )
