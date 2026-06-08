"""Metrics and scoring for pipeline outputs."""

from __future__ import annotations

from src.models import (
    PipelineMetrics,
    PipelineResult,
    VerificationCounts,
    VerificationLabel,
    VerificationResult,
)


def count_labels(results: list[VerificationResult]) -> VerificationCounts:
    counts = VerificationCounts(total_triples=len(results))
    for vr in results:
        if vr.label == VerificationLabel.SUPPORTED:
            counts.supported += 1
        elif vr.label == VerificationLabel.CONTRADICTED:
            counts.contradicted += 1
        elif vr.label == VerificationLabel.NOT_ENOUGH_INFO:
            counts.not_enough_info += 1
    return counts


def build_metrics(
    *,
    initial_verification: list[VerificationResult],
    graph_revision_needed: bool,
    revised_verification: list[VerificationResult] | None = None,
) -> PipelineMetrics:
    initial = count_labels(initial_verification)
    metrics = PipelineMetrics(
        initial_total_triples=initial.total_triples,
        initial_supported_count=initial.supported,
        initial_contradicted_count=initial.contradicted,
        initial_not_enough_info_count=initial.not_enough_info,
        graph_revision_needed=graph_revision_needed,
    )
    if revised_verification is not None:
        revised = count_labels(revised_verification)
        metrics.graph_revised_total_triples = revised.total_triples
        metrics.graph_revised_supported_count = revised.supported
        metrics.graph_revised_contradicted_count = revised.contradicted
        metrics.graph_revised_not_enough_info_count = revised.not_enough_info
    return metrics


def compute_verification_counts(result: PipelineResult) -> dict[str, int]:
    """Backward-compatible flat count dict."""
    m = result.metrics
    return {
        "total_triples": m.initial_total_triples,
        "SUPPORTED": m.initial_supported_count,
        "CONTRADICTED": m.initial_contradicted_count,
        "NOT_ENOUGH_INFO": m.initial_not_enough_info_count,
        "revision_needed": int(m.graph_revision_needed),
    }
