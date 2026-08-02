#!/usr/bin/env python3
"""Reproducible analysis of the official GraphEval Apollo 50-question experiment.

Reads the authoritative benchmark result JSON (no remembered numbers are
hard-coded) and writes a machine-readable and a human-readable analysis:

    results/research/grapheval_final_experiment_analysis.json
    results/research/grapheval_final_experiment_analysis.md

Usage:
    .venv/bin/python scripts/analyze_final_experiment.py \
        [results_json] [out_json] [out_md]

Defaults target the official run
`results/research/apollo_multihop_llama31_8b_20260727T203028Z.json`.

Concept separation (kept throughout):
- textual correctness (exact match / contains expected / normalized match) is
  post-inference scoring against the benchmark expected answer;
- pipeline resolution (resolved_by_pipeline, stop reason, evidence path) is the
  deterministic pipeline's own verdict and never sees the expected answer;
- an unresolved run is not automatically a model failure and a textually
  correct answer is not automatically a pipeline success.

Statistical caution: each designed depth contains only five questions, so
per-depth values are reported as counts with descriptive rates only. Wilson
95% confidence intervals are provided for overall proportions only.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_RESULTS = "results/research/apollo_multihop_llama31_8b_20260727T203028Z.json"
DEFAULT_OUT_JSON = "results/research/grapheval_final_experiment_analysis.json"
DEFAULT_OUT_MD = "results/research/grapheval_final_experiment_analysis.md"


def wilson_ci(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score 95% interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def quartiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {k: None for k in ("min", "q1", "median", "q3", "max", "mean")}
    ordered = sorted(values)
    if len(ordered) == 1:
        v = round(ordered[0], 3)
        return {"min": v, "q1": v, "median": v, "q3": v, "max": v, "mean": v}
    q1, q2, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
    return {
        "min": round(ordered[0], 3),
        "q1": round(q1, 3),
        "median": round(q2, 3),
        "q3": round(q3, 3),
        "max": round(ordered[-1], 3),
        "mean": round(statistics.mean(ordered), 3),
    }


def normalized_match(row: dict[str, Any]) -> bool | None:
    """Normalized-answer match using the run's own recorded normalization."""
    ne, np_ = row.get("normalized_expected"), row.get("normalized_predicted")
    if ne is None or np_ is None:
        return None
    return ne == np_ or ne in np_


def joint_category(row: dict[str, Any], textual_key: str) -> str:
    textual = bool(row.get(textual_key))
    resolved = bool(row.get("resolved_by_pipeline"))
    if textual and resolved:
        return "textually_correct_and_pipeline_resolved"
    if textual and not resolved:
        return "textually_correct_but_pipeline_unresolved"
    if not textual and resolved:
        return "textually_incorrect_but_pipeline_resolved"
    return "textually_incorrect_and_pipeline_unresolved"


def bucket(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    runtimes = [float(r.get("runtime_seconds") or 0.0) for r in rows]
    exact = sum(1 for r in rows if r.get("exact_match"))
    contains = sum(1 for r in rows if r.get("contains_expected_answer"))
    norm = sum(1 for r in rows if normalized_match(r))
    resolved = sum(1 for r in rows if r.get("resolved_by_pipeline"))
    path_complete = sum(1 for r in rows if r.get("evidence_path_complete"))
    return {
        "questions": n,
        "completed": sum(1 for r in rows if r.get("terminal_state") == "completed"),
        "errors": sum(1 for r in rows if r.get("error")),
        "timeouts": sum(1 for r in rows if r.get("terminal_state") == "timeout"),
        "exact_match": exact,
        "contains_expected": contains,
        "normalized_match": norm,
        "pipeline_resolved": resolved,
        "pipeline_unresolved": n - resolved,
        "evidence_path_complete": path_complete,
        "stop_reasons": dict(Counter(str(r.get("final_stop_reason")) for r in rows)),
        "joint_contains_x_resolved": dict(
            Counter(joint_category(r, "contains_expected_answer") for r in rows)
        ),
        "joint_exact_x_resolved": dict(
            Counter(joint_category(r, "exact_match") for r in rows)
        ),
        "iterations_total": sum(int(r.get("iterations") or 0) for r in rows),
        "revisions_total": sum(int(r.get("revisions") or 0) for r in rows),
        "avg_iterations": round(
            statistics.mean([int(r.get("iterations") or 0) for r in rows]), 3
        ) if rows else None,
        "avg_revisions": round(
            statistics.mean([int(r.get("revisions") or 0) for r in rows]), 3
        ) if rows else None,
        "runtime_seconds": quartiles(runtimes),
        "final_claim_labels": {
            "supported": sum(int(r.get("final_supported_count") or 0) for r in rows),
            "contradicted": sum(int(r.get("final_contradicted_count") or 0) for r in rows),
            "no_evidence": sum(int(r.get("final_no_evidence_count") or 0) for r in rows),
        },
        "cases_with_label": {
            "supported": sum(1 for r in rows if int(r.get("final_supported_count") or 0) > 0),
            "contradicted": sum(1 for r in rows if int(r.get("final_contradicted_count") or 0) > 0),
            "no_evidence": sum(1 for r in rows if int(r.get("final_no_evidence_count") or 0) > 0),
        },
    }


def revision_behavior(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Initial-to-final behavior, limited to what the aggregate rows support.

    The official run rows do not preserve the initial answer text, so full
    transition analysis is impossible from this file alone. What IS sound:
    - revisions == 0 implies the final answer is the unrevised first answer;
    - revisions > 0 means at least one revision occurred; only the final
      outcome of the revised answer is observable here.
    """
    unrevised = [r for r in rows if int(r.get("revisions") or 0) == 0]
    revised = [r for r in rows if int(r.get("revisions") or 0) > 0]

    def outcomes(sub: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "count": len(sub),
            "exact_match": sum(1 for r in sub if r.get("exact_match")),
            "contains_expected": sum(1 for r in sub if r.get("contains_expected_answer")),
            "pipeline_resolved": sum(1 for r in sub if r.get("resolved_by_pipeline")),
            "stop_reasons": dict(Counter(str(r.get("final_stop_reason")) for r in sub)),
        }

    return {
        "limitation": (
            "Official-run rows do not store initial answers or per-iteration claim "
            "labels (debug_log_path is null for all rows), so initial-to-final "
            "answer transitions and claim-label transitions cannot be computed for "
            "the official sample. Rows with revisions == 0 are first-pass answers "
            "by construction. Trace-level transition evidence comes from the "
            "separately preserved qualitative executions in "
            "research/REPRESENTATIVE_TRACE_CASES.md."
        ),
        "first_pass_unrevised": outcomes(unrevised),
        "revised_at_least_once": outcomes(revised),
        "revised_but_still_not_containing_expected": sum(
            1
            for r in revised
            if not r.get("contains_expected_answer")
        ),
        "revised_and_unresolved": sum(
            1 for r in revised if not r.get("resolved_by_pipeline")
        ),
        "revised_and_resolved": sum(
            1 for r in revised if r.get("resolved_by_pipeline")
        ),
    }


def main() -> None:
    argv = sys.argv[1:]
    results_path = Path(argv[0]) if len(argv) > 0 else Path(DEFAULT_RESULTS)
    out_json = Path(argv[1]) if len(argv) > 1 else Path(DEFAULT_OUT_JSON)
    out_md = Path(argv[2]) if len(argv) > 2 else Path(DEFAULT_OUT_MD)

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = payload["results"]
    runner_summary = payload.get("summary", {})

    overall = bucket(rows)
    n = overall["questions"]

    # Cross-check against the runner's own summary block; fail loudly on drift.
    checks = {
        "attempted": (runner_summary.get("attempted"), n),
        "completed": (runner_summary.get("completed"), overall["completed"]),
        "errored": (runner_summary.get("errored"), overall["errors"]),
        "exact_match_count": (runner_summary.get("exact_match_count"), overall["exact_match"]),
        "contains_expected_count": (
            runner_summary.get("contains_expected_count"),
            overall["contains_expected"],
        ),
        "pipeline_resolved_count": (
            runner_summary.get("pipeline_resolved_count"),
            overall["pipeline_resolved"],
        ),
    }
    mismatches = {k: v for k, v in checks.items() if v[0] is not None and v[0] != v[1]}
    if mismatches:
        raise SystemExit(f"Recomputed aggregates disagree with runner summary: {mismatches}")

    # The runner's own 'resolved_and_matched_count' uses its answer_match flag
    # (a more permissive textual match) rather than exact_match; report both.
    resolved_and_exact = sum(
        1 for r in rows if r.get("resolved_by_pipeline") and r.get("exact_match")
    )
    resolved_and_answer_match = sum(
        1 for r in rows if r.get("resolved_by_pipeline") and r.get("answer_match")
    )

    by_depth = defaultdict(list)
    for r in rows:
        by_depth[int(r["hop_count"])].append(r)
    depth_metrics = {str(d): bucket(v) for d, v in sorted(by_depth.items())}

    def ci(count: int) -> dict[str, Any]:
        lo, hi = wilson_ci(count, n)
        return {"count": count, "rate": round(count / n, 4), "wilson95": [lo, hi]}

    analysis: dict[str, Any] = {
        "source_results": str(results_path),
        "source_generated_at": payload.get("generated_at"),
        "test_set_id": payload.get("test_set_id"),
        "branch": payload.get("branch"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "configured_num_ctx": payload.get("configured_num_ctx"),
        "timeout_per_question_seconds": payload.get("timeout_per_question_seconds"),
        "neo4j_enabled": payload.get("neo4j_enabled"),
        "clear_neo4j_between_runs": payload.get("clear_neo4j_between_runs"),
        "dataset_validation": payload.get("validation"),
        "runner_summary_crosscheck": "all recomputed aggregates match the runner summary",
        "notes": {
            "sample_size": (
                "Five questions per designed depth; per-depth values are descriptive "
                "counts, not statistically established trends."
            ),
            "resolved_and_matched_discrepancy": (
                "The runner summary's resolved_and_matched_count "
                f"({runner_summary.get('resolved_and_matched_count')}) uses the "
                "runner's permissive answer_match flag; strict exact-match joint "
                f"count is {resolved_and_exact} and answer_match joint count is "
                f"{resolved_and_answer_match}."
            ),
            "target_satisfaction": (
                "Rows do not carry an explicit target_satisfied boolean; target "
                "failure is observable via the UNRESOLVED_TARGET_NOT_SATISFIED "
                "stop reason and the runner's target_not_satisfied failure "
                "category."
            ),
        },
        "overall": overall,
        "overall_proportions_with_ci": {
            "exact_match": ci(overall["exact_match"]),
            "contains_expected": ci(overall["contains_expected"]),
            "normalized_match": ci(overall["normalized_match"]),
            "pipeline_resolved": ci(overall["pipeline_resolved"]),
            "evidence_path_complete": ci(overall["evidence_path_complete"]),
        },
        "resolved_and_exact": resolved_and_exact,
        "resolved_and_answer_match": resolved_and_answer_match,
        "by_depth": depth_metrics,
        "revision_behavior": revision_behavior(rows),
        "failure_categories_runner": dict(
            Counter(
                str(r.get("failure_category"))
                for r in rows
                if r.get("failure_category")
            )
        ),
        "per_question": [
            {
                "id": r.get("id"),
                "execution_id": r.get("execution_id"),
                "hop_count": r.get("hop_count"),
                "exact_match": r.get("exact_match"),
                "contains_expected": r.get("contains_expected_answer"),
                "normalized_match": normalized_match(r),
                "pipeline_resolved": r.get("resolved_by_pipeline"),
                "stop_reason": r.get("final_stop_reason"),
                "iterations": r.get("iterations"),
                "revisions": r.get("revisions"),
                "final_labels_s_c_n": [
                    r.get("final_supported_count"),
                    r.get("final_contradicted_count"),
                    r.get("final_no_evidence_count"),
                ],
                "evidence_path_complete": r.get("evidence_path_complete"),
                "evidence_path_length": r.get("evidence_path_length"),
                "runtime_seconds": r.get("runtime_seconds"),
                "failure_category": r.get("failure_category"),
            }
            for r in rows
        ],
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")

    # ---------- Markdown ----------
    rt = overall["runtime_seconds"]
    jc = overall["joint_contains_x_resolved"]
    je = overall["joint_exact_x_resolved"]
    md: list[str] = [
        "# GraphEval Final Experiment Analysis",
        "",
        f"- Source: `{results_path}`",
        f"- Test set: `{payload.get('test_set_id')}` — run generated {payload.get('generated_at')}",
        f"- Branch: `{payload.get('branch')}` | provider/model: {payload.get('provider')} / {payload.get('model')}",
        f"- num_ctx {payload.get('configured_num_ctx')}, timeout {payload.get('timeout_per_question_seconds')} s/question, "
        f"Neo4j enabled: {payload.get('neo4j_enabled')}, cleared between questions: {payload.get('clear_neo4j_between_runs')}",
        "",
        "All numbers below are recomputed from the raw per-question rows; the recomputed",
        "aggregates match the runner's summary block exactly.",
        "",
        "Sample-size note: each designed depth contains only five questions. Per-depth",
        "values are descriptive counts, not statistically established trends.",
        "",
        "## Completion and runtime",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Questions | {n} |",
        f"| Completed | {overall['completed']} |",
        f"| Errors | {overall['errors']} |",
        f"| Timeouts | {overall['timeouts']} |",
        f"| Total iterations | {overall['iterations_total']} |",
        f"| Total revisions | {overall['revisions_total']} |",
        f"| Runtime s (min/Q1/median/Q3/max) | {rt['min']} / {rt['q1']} / {rt['median']} / {rt['q3']} / {rt['max']} |",
        f"| Runtime s (mean) | {rt['mean']} |",
        "",
        "## Textual-answer results (overall, n=50, Wilson 95% CI)",
        "",
        "| Metric | Count | Rate | 95% CI |",
        "|---|---|---|---|",
    ]
    for key, label in [
        ("exact_match", "Exact match"),
        ("contains_expected", "Contains expected"),
        ("normalized_match", "Normalized match"),
        ("pipeline_resolved", "Pipeline resolved"),
        ("evidence_path_complete", "Evidence path complete"),
    ]:
        c = analysis["overall_proportions_with_ci"][key]
        md.append(f"| {label} | {c['count']} | {c['rate']:.2f} | [{c['wilson95'][0]:.2f}, {c['wilson95'][1]:.2f}] |")
    md += [
        "",
        "## Stop-reason distribution",
        "",
        "| Stop reason | Count |",
        "|---|---|",
    ]
    for reason, count in sorted(overall["stop_reasons"].items(), key=lambda kv: -kv[1]):
        md.append(f"| {reason} | {count} |")
    md += [
        "",
        "## Joint textual-correctness × pipeline-resolution outcomes",
        "",
        "Textual correctness here uses contains-expected (exact-match variant in parentheses).",
        "",
        "| Joint category | Contains-expected basis | Exact-match basis |",
        "|---|---|---|",
    ]
    for cat in [
        "textually_correct_and_pipeline_resolved",
        "textually_correct_but_pipeline_unresolved",
        "textually_incorrect_but_pipeline_resolved",
        "textually_incorrect_and_pipeline_unresolved",
    ]:
        md.append(f"| {cat.replace('_', ' ')} | {jc.get(cat, 0)} | {je.get(cat, 0)} |")
    md += [
        "",
        f"Runner `resolved_and_matched_count` ({runner_summary.get('resolved_and_matched_count')}) uses the runner's",
        f"permissive `answer_match` flag; strict exact-and-resolved is {resolved_and_exact}.",
        "",
        "## Results by designed depth (five questions per depth)",
        "",
        "| Depth | Exact | Contains | Resolved | Path complete | Avg iter | Avg rev | Mean runtime s |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for d, m in depth_metrics.items():
        md.append(
            f"| {d} | {m['exact_match']}/5 | {m['contains_expected']}/5 | {m['pipeline_resolved']}/5 | "
            f"{m['evidence_path_complete']}/5 | {m['avg_iterations']} | {m['avg_revisions']} | {m['runtime_seconds']['mean']} |"
        )
    rb = analysis["revision_behavior"]
    fp, rv = rb["first_pass_unrevised"], rb["revised_at_least_once"]
    md += [
        "",
        "## Initial-to-final behavior (bounded by available data)",
        "",
        rb["limitation"],
        "",
        "| Group | Count | Exact | Contains | Resolved |",
        "|---|---|---|---|---|",
        f"| First-pass (0 revisions) | {fp['count']} | {fp['exact_match']} | {fp['contains_expected']} | {fp['pipeline_resolved']} |",
        f"| Revised (≥1 revision) | {rv['count']} | {rv['exact_match']} | {rv['contains_expected']} | {rv['pipeline_resolved']} |",
        "",
        f"- Revised and resolved: {rb['revised_and_resolved']}",
        f"- Revised but unresolved: {rb['revised_and_unresolved']}",
        f"- Revised and final answer still does not contain expected: {rb['revised_but_still_not_containing_expected']}",
        "",
        "## Final claim-label totals (last iteration of each question)",
        "",
        "| Label | Total claims | Questions containing label |",
        "|---|---|---|",
        f"| SUPPORTED | {overall['final_claim_labels']['supported']} | {overall['cases_with_label']['supported']} |",
        f"| CONTRADICTED | {overall['final_claim_labels']['contradicted']} | {overall['cases_with_label']['contradicted']} |",
        f"| NO_EVIDENCE | {overall['final_claim_labels']['no_evidence']} | {overall['cases_with_label']['no_evidence']} |",
        "",
        "Initial claim-label counts and label transitions are not recoverable from the",
        "official-run rows (see limitation above); trace-level examples appear in",
        "`research/REPRESENTATIVE_TRACE_CASES.md`.",
        "",
        "## Runner failure categories",
        "",
        "| Category | Count |",
        "|---|---|",
    ]
    for catname, count in sorted(analysis["failure_categories_runner"].items(), key=lambda kv: -kv[1]):
        md.append(f"| {catname} | {count} |")
    md.append("")
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")


if __name__ == "__main__":
    main()
