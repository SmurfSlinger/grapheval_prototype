#!/usr/bin/env python3
"""Analyze a GraphEval multihop benchmark result file (Apollo or third-domain).

Usage: analyze_benchmark_results.py <results.json> <out.analysis.json> <out.analysis.md>

Keeps these concepts separate: direct answer correctness, structured CLAIM
correctness, evidence-path correctness, question-target satisfaction, pipeline
status, Neo4j persistence correctness, transport/runtime correctness.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def classify_failure(row: dict[str, Any]) -> tuple[str, str]:
    """Return (category, evidence-based explanation) for a non-successful row.

    Only classifies when trace data supports it; otherwise 'ambiguous'.
    A row is 'successful' when exact_match and resolved_by_pipeline are true.
    """
    if row.get("terminal_state") == "timeout" or row.get("failure_category") == "timeout":
        return "timeout", "Per-question wall clock limit was reached."
    if row.get("error"):
        etype = str(row.get("error_type") or "")
        if "neo4j" in etype.lower():
            return "neo4j_failure", f"Recorded error type {etype}."
        return "other_pipeline_error", f"Recorded error: {row.get('error_message')}"

    exact = bool(row.get("exact_match"))
    contains = bool(row.get("contains_expected_answer"))
    resolved = bool(row.get("resolved_by_pipeline"))
    supported = int(row.get("final_supported_count") or 0)
    contradicted = int(row.get("final_contradicted_count") or 0)
    no_evidence = int(row.get("final_no_evidence_count") or 0)
    path_complete = bool(row.get("evidence_path_complete"))
    stop = str(row.get("final_stop_reason") or "")
    claim_count = int(row.get("claim_count") or 0)

    if exact and resolved:
        return "success", "Exact answer and honest pipeline resolution."

    if not contains and not exact:
        # The model's direct answer was wrong regardless of pipeline behavior.
        if contradicted > 0:
            return (
                "wrong_direct_answer",
                "Predicted answer differs from expected and at least one CLAIM was "
                "CONTRADICTED by trusted FACTS.",
            )
        if supported == 0 and no_evidence > 0:
            return (
                "wrong_direct_answer",
                "Predicted answer differs from expected; claims found NO_EVIDENCE "
                "support in the trusted graph.",
            )
        return (
            "wrong_direct_answer",
            "Predicted answer differs from expected answer text.",
        )

    # Correct (contains expected) but not fully successful.
    if contains and not resolved:
        if claim_count == 0:
            return (
                "claim_extraction_error",
                "Answer text contains the expected value but no claims were extracted.",
            )
        if supported > 0 and not path_complete:
            return (
                "evidence_path_resolution_error",
                "Supported terminal claim exists but the trusted evidence path did "
                "not complete to the claim.",
            )
        if supported > 0 and path_complete and stop.startswith("UNRESOLVED_TARGET"):
            return (
                "target_frame_error",
                "Supported claims and a complete path exist but the derived question "
                "target was not recognized as satisfied.",
            )
        if supported == 0 and no_evidence > 0:
            return (
                "claim_extraction_error",
                "Answer text contains the expected value but extracted claims did not "
                "match trusted FACTS (NO_EVIDENCE).",
            )
        return (
            "ambiguous",
            f"Contains expected answer but unresolved (stop={stop}); trace data does "
            "not isolate a single stage.",
        )

    if exact and not resolved:
        return (
            "target_frame_error" if stop.startswith("UNRESOLVED_TARGET") else "ambiguous",
            f"Exact answer with unresolved pipeline (stop={stop}).",
        )

    if resolved and not exact:
        if contains:
            return (
                "aggregation_projection_failure",
                "Pipeline resolved and answer contains expected value but exact-match "
                "normalization failed.",
            )
        return (
            "wrong_direct_answer",
            "Pipeline resolved a supported claim chain whose answer text does not "
            "match the benchmark expected answer.",
        )

    return "ambiguous", "Insufficient trace data to attribute a single cause."


def mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 2) if values else None


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 2) if values else None


def bucket_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    runtimes = [float(r.get("runtime_seconds") or 0) for r in rows]
    completed = [r for r in rows if r.get("terminal_state") == "completed"]
    return {
        "attempted": len(rows),
        "completed": len(completed),
        "errors": sum(1 for r in rows if r.get("error")),
        "timeouts": sum(1 for r in rows if r.get("terminal_state") == "timeout"),
        "exact_match": sum(1 for r in rows if r.get("exact_match")),
        "contains_expected": sum(1 for r in rows if r.get("contains_expected_answer")),
        "pipeline_resolved": sum(1 for r in rows if r.get("resolved_by_pipeline")),
        "resolved_and_matched": sum(
            1 for r in rows if r.get("resolved_by_pipeline") and r.get("exact_match")
        ),
        "resolved_but_wrong": sum(
            1 for r in rows if r.get("resolved_by_pipeline") and not r.get("exact_match")
        ),
        "unresolved_but_contains_expected": sum(
            1
            for r in rows
            if not r.get("resolved_by_pipeline") and r.get("contains_expected_answer")
        ),
        "avg_runtime_seconds": mean(runtimes),
        "median_runtime_seconds": median(runtimes),
        "avg_iterations": mean([float(r.get("iterations") or 0) for r in rows]),
        "avg_revisions": mean([float(r.get("revisions") or 0) for r in rows]),
        "supported_claims": sum(int(r.get("final_supported_count") or 0) for r in rows),
        "contradicted_claims": sum(int(r.get("final_contradicted_count") or 0) for r in rows),
        "no_evidence_claims": sum(int(r.get("final_no_evidence_count") or 0) for r in rows),
        "evidence_path_complete": sum(1 for r in rows if r.get("evidence_path_complete")),
        "neo4j_readback_evaluations": sum(
            1 for r in rows if r.get("kgc_evaluation_source") == "neo4j_readback"
        ),
    }


def main() -> None:
    results_path = Path(sys.argv[1])
    out_json = Path(sys.argv[2])
    out_md = Path(sys.argv[3])
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    rows = payload["results"]

    per_question = []
    failure_counts: Counter[str] = Counter()
    for row in rows:
        category, explanation = classify_failure(row)
        failure_counts[category] += 1
        terminal_claim = row.get("terminal_claim") or {}
        per_question.append(
            {
                "id": row.get("id"),
                "hop_count": row.get("hop_count"),
                "question": row.get("question"),
                "expected_answer": row.get("expected_answer"),
                "predicted_answer": row.get("predicted_answer"),
                "exact_match": row.get("exact_match"),
                "contains_expected": row.get("contains_expected_answer"),
                "pipeline_resolved": row.get("resolved_by_pipeline"),
                "stop_reason": row.get("final_stop_reason"),
                "iterations": row.get("iterations"),
                "revisions": row.get("revisions"),
                "final_claim_labels": {
                    "supported": row.get("final_supported_count"),
                    "contradicted": row.get("final_contradicted_count"),
                    "no_evidence": row.get("final_no_evidence_count"),
                },
                "terminal_claim": terminal_claim,
                "evidence_path_length": row.get("evidence_path_length"),
                "evidence_path_complete": row.get("evidence_path_complete"),
                "target_intent": (row.get("derived_question_target") or {}).get("intent"),
                "execution_id": row.get("execution_id"),
                "runtime_seconds": row.get("runtime_seconds"),
                "failure_attribution": category,
                "explanation": explanation,
            }
        )

    by_depth: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_depth[int(row["hop_count"])].append(row)

    overall = bucket_metrics(rows)
    depth_metrics = {
        str(depth): bucket_metrics(bucket) for depth, bucket in sorted(by_depth.items())
    }

    # Representative UI demonstration cases.
    def pick(pred, sort_key=None, reverse=False):
        candidates = [q for q in per_question if pred(q)]
        if sort_key:
            candidates.sort(key=sort_key, reverse=reverse)
        return candidates[0] if candidates else None

    low_success = pick(
        lambda q: q["failure_attribution"] == "success" and q["hop_count"] <= 2,
        sort_key=lambda q: q["hop_count"],
    )
    high_success = pick(
        lambda q: q["failure_attribution"] == "success",
        sort_key=lambda q: q["hop_count"],
        reverse=True,
    )
    correct_unresolved = pick(
        lambda q: q["contains_expected"] and not q["pipeline_resolved"]
    )
    model_failure = pick(lambda q: q["failure_attribution"] == "wrong_direct_answer")
    pipeline_failure = pick(
        lambda q: q["failure_attribution"]
        in {
            "claim_extraction_error",
            "relation_direction_error",
            "schema_alignment_error",
            "target_frame_error",
            "evidence_path_resolution_error",
            "aggregation_projection_failure",
        }
    )

    representatives = {
        "clean_low_depth_success": low_success,
        "clean_high_depth_success": high_success,
        "correct_answer_but_unresolved": correct_unresolved,
        "genuine_model_answer_failure": model_failure,
        "structured_claim_or_pipeline_failure": pipeline_failure,
    }

    analysis = {
        "source_results": str(results_path),
        "test_set_id": payload.get("test_set_id"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "branch": payload.get("branch"),
        "generated_at": payload.get("generated_at"),
        "configured_num_ctx": payload.get("configured_num_ctx"),
        "timeout_per_question_seconds": payload.get("timeout_per_question_seconds"),
        "neo4j_enabled": payload.get("neo4j_enabled"),
        "clear_neo4j_between_runs": payload.get("clear_neo4j_between_runs"),
        "sample_size_note": (
            "Only five questions exist per designed depth; per-depth percentages have "
            "very small sample sizes and must not be treated as statistically "
            "significant."
        ),
        "concept_separation_note": (
            "Direct answer correctness, structured CLAIM correctness, evidence-path "
            "correctness, question-target satisfaction, pipeline status, Neo4j "
            "persistence, and transport/runtime health are reported separately; an "
            "unresolved result is not automatically a model failure."
        ),
        "overall": overall,
        "by_depth": depth_metrics,
        "failure_categories": dict(failure_counts.most_common()),
        "representative_ui_cases": {
            key: (
                {
                    "id": value["id"],
                    "execution_id": value["execution_id"],
                    "hop_count": value["hop_count"],
                    "summary": value["explanation"],
                }
                if value
                else None
            )
            for key, value in representatives.items()
        },
        "per_question_appendix": per_question,
    }
    out_json.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# Benchmark Analysis: {payload.get('test_set_id')}",
        "",
        f"- Source: `{results_path}`",
        f"- Provider/model: {payload.get('provider')} / {payload.get('model')}",
        f"- Branch: {payload.get('branch')}",
        f"- Generated: {payload.get('generated_at')}",
        f"- num_ctx={payload.get('configured_num_ctx')}, timeout="
        f"{payload.get('timeout_per_question_seconds')}s, neo4j="
        f"{payload.get('neo4j_enabled')}, cleared-between-questions="
        f"{payload.get('clear_neo4j_between_runs')}",
        "",
        "Sample-size note: five questions per designed depth — depth-level rates are "
        "small-sample descriptions, not statistically significant estimates.",
        "",
        "## Overall",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for key, value in overall.items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        "## By designed depth",
        "",
        "| Depth | Attempted | Exact | Contains | Resolved | Resolved+Exact | "
        "Unresolved-but-contains | Path complete | Avg runtime s | Avg iters | Avg revs |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for depth, m in depth_metrics.items():
        lines.append(
            f"| {depth} | {m['attempted']} | {m['exact_match']} | {m['contains_expected']} | "
            f"{m['pipeline_resolved']} | {m['resolved_and_matched']} | "
            f"{m['unresolved_but_contains_expected']} | {m['evidence_path_complete']} | "
            f"{m['avg_runtime_seconds']} | {m['avg_iterations']} | {m['avg_revisions']} |"
        )
    lines += ["", "## Failure attribution", "", "| Category | Count |", "|---|---|"]
    for category, count in failure_counts.most_common():
        lines.append(f"| {category} | {count} |")
    lines += ["", "## Representative UI cases", ""]
    for key, value in analysis["representative_ui_cases"].items():
        if value:
            lines.append(
                f"- **{key}**: `{value['id']}` (hop {value['hop_count']}) — execution "
                f"`{value['execution_id']}` — {value['summary']}"
            )
        else:
            lines.append(f"- **{key}**: none present in this run")
    lines += [
        "",
        "## Per-question appendix",
        "",
        "| ID | Hop | Exact | Contains | Resolved | Stop | Iter | Rev | S/C/N | "
        "Path len | Path complete | Attribution |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for q in per_question:
        labels = q["final_claim_labels"]
        lines.append(
            f"| {q['id']} | {q['hop_count']} | {q['exact_match']} | {q['contains_expected']} | "
            f"| {q['stop_reason']} | {q['iterations']} | {q['revisions']} | "
            f"{labels['supported']}/{labels['contradicted']}/{labels['no_evidence']} | "
            f"{q['evidence_path_length']} | {q['evidence_path_complete']} | "
            f"{q['failure_attribution']} |".replace("| | ", f"| {q['pipeline_resolved']} | ")
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    print(json.dumps({"overall": overall, "failures": dict(failure_counts)}, indent=2))


if __name__ == "__main__":
    main()
