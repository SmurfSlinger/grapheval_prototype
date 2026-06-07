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
class PipelineResult:
    example_id: str
    question: str
    context: str
    initial_answer: str
    extracted_triples: list[Triple] = field(default_factory=list)
    verification_results: list[VerificationResult] = field(default_factory=list)
    feedback: list[FeedbackItem] = field(default_factory=list)
    revised_answer: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
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
            "revised_answer": self.revised_answer,
        }
