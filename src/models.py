"""Data models for the hallucination feedback pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class VerificationLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_ENOUGH_INFO = "NOT_ENOUGH_INFO"


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
