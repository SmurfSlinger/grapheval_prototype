"""Data models for the hallucination feedback pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class VerificationLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_ENOUGH_INFO = "NOT_ENOUGH_INFO"


class KgcClaimLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NO_EVIDENCE = "NO_EVIDENCE"


class SubQuestionStopReason(str, Enum):
    RESOLVED = "RESOLVED"
    STALLED = "STALLED"
    UNRESOLVED_NO_EVIDENCE = "UNRESOLVED_NO_EVIDENCE"
    UNRESOLVED_TARGET_NOT_SATISFIED = "UNRESOLVED_TARGET_NOT_SATISFIED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    GENERATION_FAILED = "GENERATION_FAILED"
    NO_CLAIMS_EXTRACTED = "NO_CLAIMS_EXTRACTED"


class KgcProvenanceType(str, Enum):
    TRUSTED_CONTEXT = "trusted_context"
    SUPPORTED_BY_EXISTING_KGC = "supported_by_existing_kgc"
    DERIVED_FROM_SUPPORTED_FACTS = "derived_from_supported_facts"
    DERIVED_FROM_TRUSTED_CONTEXT = "derived_from_trusted_context"
    EXTERNALLY_RETRIEVED_AND_VALIDATED = "externally_retrieved_and_validated"


@dataclass
class Example:
    id: str
    question: str
    context: str
    initial_answer: Optional[str] = None


@dataclass
class Triple:
    subject: str
    relation: str
    object: str
    source_sentence: Optional[str] = None


@dataclass
class VerificationResult:
    triple: Triple
    label: VerificationLabel
    evidence: str
    reason: str


@dataclass
class FeedbackItem:
    triple: Triple
    status: VerificationLabel
    instruction: str
    evidence: str


@dataclass
class KgcFact:
    subject: str
    relation: str
    object: str
    evidence: Optional[str] = None


@dataclass
class KgcEvaluationResult:
    triple: Triple
    label: KgcClaimLabel
    reason: str
    evidence: str
    conflicting_object: Optional[str] = None
    conflicting_fact: Optional[KgcFact] = None
    matched_kgc_fact: Optional[KgcFact] = None
    original_claim: Optional[Triple] = None
    source_sentence: Optional[str] = None
    backtracking_action: Optional[str] = None


@dataclass
class BacktrackingTrace:
    answer_0_source: str
    answer_0_mode: str
    kgc_source: str
    answer_n_source: str
    claim_extraction_source: str
    revision_source: str
    answer_0_warning: Optional[str] = None
    kgc_reference_answer_source: Optional[str] = None


@dataclass
class RevisionEffect:
    preserved_supported_count: int = 0
    corrected_contradicted_count: int = 0
    removed_or_deferred_no_evidence_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BacktrackingFeedbackItem:
    triple: Triple
    label: KgcClaimLabel
    instruction: str
    reason: str
    evidence: str
    conflicting_object: Optional[str] = None
    matched_kgc_fact: Optional[KgcFact] = None
    conflicting_fact: Optional[KgcFact] = None
    backtracking_action: Optional[str] = None


@dataclass
class BacktrackingResult:
    example_id: str
    question: str
    context: str
    answer_0: str
    kgc_facts: list[KgcFact] = field(default_factory=list)
    serialized_kgc: str = ""
    kgc_reference_answer: str = ""
    graph_grounded_answer: str = ""
    answer_n: str = ""
    evaluated_answer: str = ""
    evaluated_answer_iteration: int = 0
    iteration: int = 0
    evaluated_claims: list[KgcEvaluationResult] = field(default_factory=list)
    backtracking_feedback: list[BacktrackingFeedbackItem] = field(default_factory=list)
    answer_1: str = ""
    answer_n_plus_1: str = ""
    final_answer: str = ""
    supported_count: int = 0
    contradicted_count: int = 0
    no_evidence_count: int = 0
    max_iterations: int = 1
    extracted_claims: list[Triple] = field(default_factory=list)
    aligned_claims: list[Triple] = field(default_factory=list)
    trace: BacktrackingTrace | None = None
    revision_effect: RevisionEffect | None = None
    answer_0_mode: str = "preset"
    answer_0_warning: Optional[str] = None
    kgc_extraction_notice: Optional[str] = None
    stop_reason: Optional[str] = None
    iteration_history: list[dict[str, Any]] = field(default_factory=list)
    execution_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        def _triple_dict(t: Triple) -> dict[str, Any]:
            return asdict(t)

        def _fact_dict(f: KgcFact | None) -> dict[str, Any] | None:
            return asdict(f) if f else None

        def _eval_dict(ev: KgcEvaluationResult) -> dict[str, Any]:
            return {
                "triple": _triple_dict(ev.triple),
                "aligned_claim": _triple_dict(ev.triple),
                "original_claim": (
                    _triple_dict(ev.original_claim) if ev.original_claim else None
                ),
                "schema_aligned": ev.original_claim is not None,
                "source_sentence": ev.source_sentence,
                "label": ev.label.value,
                "reason": ev.reason,
                "evidence": ev.evidence,
                "matched_kgc_fact": _fact_dict(ev.matched_kgc_fact),
                "conflicting_object": ev.conflicting_object,
                "conflicting_fact": _fact_dict(ev.conflicting_fact),
                "backtracking_action": ev.backtracking_action,
            }

        kgc_reference = self.kgc_reference_answer or self.graph_grounded_answer
        evaluated = self.evaluated_answer or self.answer_n or self.answer_0
        answer_1 = self.answer_1 or self.answer_n_plus_1
        final = self.final_answer or answer_1 or self.answer_0

        return {
            "example_id": self.example_id,
            "execution_id": self.execution_id,
            "question": self.question,
            "context": self.context,
            "answer_0": self.answer_0,
            "kgc_facts": [asdict(f) for f in self.kgc_facts],
            "serialized_kgc": self.serialized_kgc,
            "kgc_reference_answer": kgc_reference,
            "graph_grounded_answer": kgc_reference,
            "answer_n": evaluated,
            "evaluated_answer": evaluated,
            "evaluated_answer_iteration": self.evaluated_answer_iteration,
            "iteration": self.iteration,
            "extracted_claims": [_triple_dict(t) for t in self.extracted_claims],
            "aligned_claims": [_triple_dict(t) for t in self.aligned_claims],
            "evaluated_claims": [_eval_dict(ev) for ev in self.evaluated_claims],
            "backtracking_feedback": [
                {
                    "triple": _triple_dict(fb.triple),
                    "label": fb.label.value,
                    "instruction": fb.instruction,
                    "reason": fb.reason,
                    "evidence": fb.evidence,
                    "conflicting_object": fb.conflicting_object,
                    "matched_kgc_fact": _fact_dict(fb.matched_kgc_fact),
                    "conflicting_fact": _fact_dict(fb.conflicting_fact),
                    "backtracking_action": fb.backtracking_action,
                }
                for fb in self.backtracking_feedback
            ],
            "answer_1": answer_1,
            "answer_n_plus_1": answer_1,
            "final_answer": final,
            "supported_count": self.supported_count,
            "contradicted_count": self.contradicted_count,
            "no_evidence_count": self.no_evidence_count,
            "max_iterations": self.max_iterations,
            "trace": asdict(self.trace) if self.trace else None,
            "revision_effect": (
                self.revision_effect.to_dict() if self.revision_effect else None
            ),
            "answer_0_mode": self.answer_0_mode,
            "answer_0_warning": self.answer_0_warning,
            "kgc_extraction_notice": self.kgc_extraction_notice,
            "stop_reason": self.stop_reason,
            "iteration_history": self.iteration_history,
        }


@dataclass
class SubQuestion:
    id: int
    question: str


@dataclass
class SubQuestionInitialAnswer:
    sub_question_id: int
    answer: str


@dataclass
class KgcCandidateUpdate:
    fact: KgcFact
    provenance: KgcProvenanceType
    sub_question_id: int | None = None
    iteration: int | None = None
    promoted: bool = False
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact": asdict(self.fact),
            "provenance": self.provenance.value,
            "sub_question_id": self.sub_question_id,
            "iteration": self.iteration,
            "promoted": self.promoted,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class WorkingKgcAddition:
    fact: KgcFact
    provenance: KgcProvenanceType
    extraction_scope: str
    sub_question_id: int | None = None
    dedupe_note: str | None = None
    derivation_type: str | None = None
    evidence_spans: list[str] = field(default_factory=list)
    derivation_explanation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact": asdict(self.fact),
            "provenance": self.provenance.value,
            "extraction_scope": self.extraction_scope,
            "sub_question_id": self.sub_question_id,
            "dedupe_note": self.dedupe_note,
            "derivation_type": self.derivation_type,
            "evidence_spans": self.evidence_spans,
            "derivation_explanation": self.derivation_explanation,
        }


@dataclass
class SubQuestionIteration:
    iteration: int
    answer: str
    extracted_claims: list[Triple] = field(default_factory=list)
    aligned_claims: list[Triple] = field(default_factory=list)
    evaluated_claims: list[KgcEvaluationResult] = field(default_factory=list)
    pre_enrichment_evaluated_claims: list[KgcEvaluationResult] = field(
        default_factory=list
    )
    backtracking_feedback: list[BacktrackingFeedbackItem] = field(default_factory=list)
    supported_count: int = 0
    contradicted_count: int = 0
    no_evidence_count: int = 0
    evaluation_signature: str = ""
    focused_enrichment_applied: bool = False
    focused_facts_added: list[KgcFact] = field(default_factory=list)
    question_target: dict[str, Any] | None = None
    target_satisfied: bool = False
    on_target_supported_count: int = 0
    supported_but_irrelevant_count: int = 0
    unsupported_target_count: int = 0
    answer_is_abstention: bool = False
    pre_enrichment_no_evidence_count: int = 0
    target_frame_trace: dict[str, int] | None = None
    abstention_stop_reason: str | None = None
    focused_extraction_raw: list[KgcFact] = field(default_factory=list)
    focused_extraction_filtered: list[KgcFact] = field(default_factory=list)
    derived_facts_added: list[KgcFact] = field(default_factory=list)
    derivation_trace: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        def _triple_dict(t: Triple) -> dict[str, Any]:
            return asdict(t)

        def _eval_dict(ev: KgcEvaluationResult) -> dict[str, Any]:
            return {
                "triple": _triple_dict(ev.triple),
                "label": ev.label.value,
                "reason": ev.reason,
                "evidence": ev.evidence,
                "conflicting_object": ev.conflicting_object,
                "conflicting_fact": asdict(ev.conflicting_fact)
                if ev.conflicting_fact
                else None,
                "matched_kgc_fact": asdict(ev.matched_kgc_fact)
                if ev.matched_kgc_fact
                else None,
                "backtracking_action": ev.backtracking_action,
            }

        return {
            "iteration": self.iteration,
            "answer": self.answer,
            "extracted_claims": [_triple_dict(t) for t in self.extracted_claims],
            "aligned_claims": [_triple_dict(t) for t in self.aligned_claims],
            "evaluated_claims": [_eval_dict(ev) for ev in self.evaluated_claims],
            "pre_enrichment_evaluated_claims": [
                _eval_dict(ev) for ev in self.pre_enrichment_evaluated_claims
            ],
            "backtracking_feedback": [
                {
                    "triple": _triple_dict(fb.triple),
                    "label": fb.label.value,
                    "instruction": fb.instruction,
                    "reason": fb.reason,
                    "evidence": fb.evidence,
                    "conflicting_object": fb.conflicting_object,
                    "matched_kgc_fact": asdict(fb.matched_kgc_fact)
                    if fb.matched_kgc_fact
                    else None,
                    "conflicting_fact": asdict(fb.conflicting_fact)
                    if fb.conflicting_fact
                    else None,
                    "backtracking_action": fb.backtracking_action,
                }
                for fb in self.backtracking_feedback
            ],
            "supported_count": self.supported_count,
            "contradicted_count": self.contradicted_count,
            "no_evidence_count": self.no_evidence_count,
            "evaluation_signature": self.evaluation_signature,
            "focused_enrichment_applied": self.focused_enrichment_applied,
            "focused_facts_added": [asdict(f) for f in self.focused_facts_added],
            "question_target": self.question_target,
            "target_satisfied": self.target_satisfied,
            "on_target_supported_count": self.on_target_supported_count,
            "supported_but_irrelevant_count": self.supported_but_irrelevant_count,
            "unsupported_target_count": self.unsupported_target_count,
            "answer_is_abstention": self.answer_is_abstention,
            "pre_enrichment_no_evidence_count": self.pre_enrichment_no_evidence_count,
            "target_frame_trace": self.target_frame_trace,
            "abstention_stop_reason": self.abstention_stop_reason,
            "focused_extraction_raw": [asdict(f) for f in self.focused_extraction_raw],
            "focused_extraction_filtered": [
                asdict(f) for f in self.focused_extraction_filtered
            ],
            "derived_facts_added": [asdict(f) for f in self.derived_facts_added],
            "derivation_trace": self.derivation_trace,
        }


@dataclass
class SubQuestionResult:
    sub_question_id: int
    question: str
    initial_answer: str
    final_answer: str
    stop_reason: SubQuestionStopReason
    iteration_count: int
    iteration_history: list[SubQuestionIteration] = field(default_factory=list)
    supported_count: int = 0
    contradicted_count: int = 0
    no_evidence_count: int = 0
    final_supported: int = 0
    final_contradicted: int = 0
    final_no_evidence: int = 0
    cumulative_supported_evaluations: int = 0
    cumulative_contradicted_evaluations: int = 0
    cumulative_no_evidence_evaluations: int = 0
    focused_facts_added_count: int = 0
    proactive_focused_facts_added: int = 0
    reactive_focused_facts_added: int = 0
    working_kgc_count_after: int = 0
    initial_supported: int = 0
    initial_contradicted: int = 0
    initial_no_evidence: int = 0
    revision_count: int = 0
    resolved_without_revision: bool = False
    question_target: dict[str, Any] | None = None
    question_target_satisfied: bool = False
    supported_but_irrelevant_count: int = 0
    unsupported_target_count: int = 0
    focused_extraction_raw: list[KgcFact] = field(default_factory=list)
    focused_extraction_filtered: list[KgcFact] = field(default_factory=list)
    focused_extraction_merged: list[KgcFact] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub_question_id": self.sub_question_id,
            "question": self.question,
            "initial_answer": self.initial_answer,
            "final_answer": self.final_answer,
            "stop_reason": self.stop_reason.value,
            "iteration_count": self.iteration_count,
            "iteration_history": [item.to_dict() for item in self.iteration_history],
            "supported_count": self.supported_count,
            "contradicted_count": self.contradicted_count,
            "no_evidence_count": self.no_evidence_count,
            "final_supported": self.final_supported,
            "final_contradicted": self.final_contradicted,
            "final_no_evidence": self.final_no_evidence,
            "cumulative_supported_evaluations": self.cumulative_supported_evaluations,
            "cumulative_contradicted_evaluations": (
                self.cumulative_contradicted_evaluations
            ),
            "cumulative_no_evidence_evaluations": (
                self.cumulative_no_evidence_evaluations
            ),
            "focused_facts_added_count": self.focused_facts_added_count,
            "proactive_focused_facts_added": self.proactive_focused_facts_added,
            "reactive_focused_facts_added": self.reactive_focused_facts_added,
            "working_kgc_count_after": self.working_kgc_count_after,
            "initial_supported": self.initial_supported,
            "initial_contradicted": self.initial_contradicted,
            "initial_no_evidence": self.initial_no_evidence,
            "revision_count": self.revision_count,
            "resolved_without_revision": self.resolved_without_revision,
            "question_target": self.question_target,
            "question_target_satisfied": self.question_target_satisfied,
            "supported_but_irrelevant_count": self.supported_but_irrelevant_count,
            "unsupported_target_count": self.unsupported_target_count,
            "focused_extraction_raw": [asdict(f) for f in self.focused_extraction_raw],
            "focused_extraction_filtered": [
                asdict(f) for f in self.focused_extraction_filtered
            ],
            "focused_extraction_merged": [
                asdict(f) for f in self.focused_extraction_merged
            ],
        }


@dataclass
class DecomposedBacktrackingTrace:
    mode: str = "decomposed_iterative_kgc"
    kgc_source: str = "extracted_from_trusted_context"
    question_split_source: str = "llm_question_decomposition"
    claim_extraction_source: str = "extracted_from_answer_n"
    revision_source: str = "generated_from_answer_n_plus_kgc_plus_backtracking_feedback"
    combine_source: str = "deterministic_sub_answer_concatenation"
    working_kgc_auto_promote: bool = False
    structured_output_retries: int = 0
    answer_0_mode: str = "generated_per_sub_question"
    provider_class: str | None = None
    model: str | None = None
    example_id: str | None = None
    execution_id: str | None = None
    benchmark_id: str | None = None
    question_id: str | None = None
    context_extraction_format: str | None = None
    context_extraction_trace: dict[str, Any] | None = None
    stage_providers: dict[str, str] = field(default_factory=dict)
    compound_answer_0_source: str | None = None
    projection_trace_retries: int = 0
    projection_method: str | None = None
    projection_source: str | None = None
    projection_faithfulness_passed: bool | None = None
    configured_num_ctx: int | None = None
    llm_call_telemetry: list[dict[str, Any]] = field(default_factory=list)
    neo4j_enabled: bool = False
    neo4j_cleared_before_run: bool = False
    neo4j_base_facts_persisted: int = 0
    neo4j_working_facts_persisted: int = 0
    kgc_evaluation_source: str = "in_memory"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecomposedExperimentMetrics:
    sub_question_count: int = 0
    total_iterations: int = 0
    total_claims_extracted: int = 0
    total_claims_evaluated: int = 0
    total_supported: int = 0
    total_contradicted: int = 0
    total_no_evidence: int = 0
    final_supported: int = 0
    final_contradicted: int = 0
    final_no_evidence: int = 0
    cumulative_supported_evaluations: int = 0
    cumulative_contradicted_evaluations: int = 0
    cumulative_no_evidence_evaluations: int = 0
    structured_output_retries: int = 0
    resolved_sub_questions: int = 0
    stalled_sub_questions: int = 0
    unresolved_sub_questions: int = 0
    max_iterations_sub_questions: int = 0
    generation_failed_sub_questions: int = 0
    no_claims_sub_questions: int = 0
    total_initial_contradicted: int = 0
    total_initial_no_evidence: int = 0
    total_revisions: int = 0
    corrected_claims_count: int = 0
    resolved_without_revision_count: int = 0
    resolved_after_revision_count: int = 0
    compound_answer_0: str = ""
    unsupported_target_count: int = 0
    supported_but_irrelevant_count: int = 0
    unresolved_target_not_satisfied_count: int = 0
    pre_enrichment_no_evidence_events: int = 0
    post_enrichment_no_evidence_events: int = 0
    abstention_stops: int = 0
    target_frame_normalizations: int = 0
    relation_family_matches: int = 0
    subject_alias_matches: int = 0
    target_scoped_fact_projections: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["total_supported"] = self.cumulative_supported_evaluations
        data["total_contradicted"] = self.cumulative_contradicted_evaluations
        data["total_no_evidence"] = self.cumulative_no_evidence_evaluations
        return data


@dataclass
class DecomposedBacktrackingResult:
    example_id: str
    original_question: str
    context: str
    execution_id: str | None = None
    sub_questions: list[SubQuestion] = field(default_factory=list)
    sub_question_results: list[SubQuestionResult] = field(default_factory=list)
    combined_answer: str = ""
    base_kgc_facts: list[KgcFact] = field(default_factory=list)
    working_kgc_facts: list[KgcFact] = field(default_factory=list)
    working_kgc_additions: list[WorkingKgcAddition] = field(default_factory=list)
    candidate_kgc_updates: list[KgcCandidateUpdate] = field(default_factory=list)
    trace: DecomposedBacktrackingTrace | None = None
    metrics: DecomposedExperimentMetrics | None = None
    carry_forward_context: str = ""
    max_iterations_per_sub_question: int = 3
    debug_log_path: str | None = None
    structured_triple_anomalies: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "execution_id": self.execution_id,
            "original_question": self.original_question,
            "context": self.context,
            "sub_questions": [asdict(sq) for sq in self.sub_questions],
            "sub_question_results": [r.to_dict() for r in self.sub_question_results],
            "combined_answer": self.combined_answer,
            "base_kgc_facts": [asdict(f) for f in self.base_kgc_facts],
            "working_kgc_facts": [asdict(f) for f in self.working_kgc_facts],
            "working_kgc_additions": [a.to_dict() for a in self.working_kgc_additions],
            "candidate_kgc_updates": [u.to_dict() for u in self.candidate_kgc_updates],
            "trace": self.trace.to_dict() if self.trace else None,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "carry_forward_context": self.carry_forward_context,
            "max_iterations_per_sub_question": self.max_iterations_per_sub_question,
            "debug_log_path": self.debug_log_path,
            "structured_triple_anomalies": list(self.structured_triple_anomalies),
        }


@dataclass
class VerificationCounts:
    total_triples: int = 0
    supported: int = 0
    contradicted: int = 0
    not_enough_info: int = 0


@dataclass
class PipelineMetrics:
    initial_total_triples: int = 0
    initial_supported_count: int = 0
    initial_contradicted_count: int = 0
    initial_not_enough_info_count: int = 0
    graph_revision_needed: bool = False
    graph_revised_total_triples: Optional[int] = None
    graph_revised_supported_count: Optional[int] = None
    graph_revised_contradicted_count: Optional[int] = None
    graph_revised_not_enough_info_count: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineResult:
    example_id: str
    question: str
    context: str
    initial_answer: str
    execution_id: str | None = None
    extracted_triples: list[Triple] = field(default_factory=list)
    verification_results: list[VerificationResult] = field(default_factory=list)
    feedback: list[FeedbackItem] = field(default_factory=list)
    revised_answer: Optional[str] = None
    self_corrected_answer: Optional[str] = None
    graph_feedback_revised_answer: Optional[str] = None
    graph_revised_triples: list[Triple] = field(default_factory=list)
    graph_revised_verification_results: list[VerificationResult] = field(
        default_factory=list
    )
    metrics: PipelineMetrics = field(default_factory=PipelineMetrics)

    def to_dict(self) -> dict[str, Any]:
        graph_answer = self.graph_feedback_revised_answer or self.revised_answer
        return {
            "example_id": self.example_id,
            "execution_id": self.execution_id,
            "question": self.question,
            "context": self.context,
            "initial_answer": self.initial_answer,
            "extracted_triples": [asdict(t) for t in self.extracted_triples],
            "verification_results": [
                {
                    "triple": asdict(vr.triple),
                    "label": vr.label.value,
                    "evidence": vr.evidence,
                    "reason": vr.reason,
                }
                for vr in self.verification_results
            ],
            "feedback": [
                {
                    "triple": asdict(fb.triple),
                    "status": fb.status.value,
                    "instruction": fb.instruction,
                    "evidence": fb.evidence,
                }
                for fb in self.feedback
            ],
            "revised_answer": graph_answer,
            "self_corrected_answer": self.self_corrected_answer,
            "graph_feedback_revised_answer": graph_answer,
            "graph_revised_triples": [asdict(t) for t in self.graph_revised_triples],
            "graph_revised_verification_results": [
                {
                    "triple": asdict(vr.triple),
                    "label": vr.label.value,
                    "evidence": vr.evidence,
                    "reason": vr.reason,
                }
                for vr in self.graph_revised_verification_results
            ],
            "metrics": self.metrics.to_dict(),
        }
