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
