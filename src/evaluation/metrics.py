"""Simple metrics over verification results."""

from __future__ import annotations

from src.models import PipelineResult, VerificationLabel


def compute_verification_counts(result: PipelineResult) -> dict[str, int]:
    counts = {label.value: 0 for label in VerificationLabel}
    for vr in result.verification_results:
        counts[vr.label.value] += 1
    counts["total_triples"] = len(result.extracted_triples)
    counts["revision_needed"] = int(bool(result.feedback))
    return counts
