#!/usr/bin/env python3
"""Three-run repeatability analysis for the GraphEval Apollo experiment.

Loads exactly three complete runs of the same 50-question benchmark:
Run 1 (the official frozen run) plus two exact-configuration repetitions,
verifies configuration compatibility (hard fail on mismatch), and quantifies
which outputs remained stable and which varied.

Usage:
    .venv/bin/python scripts/analyze_repeatability_experiment.py \
        <run1.json> <run2.json> <run3.json> [out.json] [out.md]

The three runs are repeated measurements of the same 50 questions — they are
never pooled into 150 independent samples, and three runs are not presented
as strong statistical inference.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_OUT_JSON = "results/research/repeatability/grapheval_repeatability_analysis.json"
DEFAULT_OUT_MD = "results/research/repeatability/grapheval_repeatability_analysis.md"

RUN_NAMES = ["run1", "run2", "run3"]

# Configuration fields that must be identical across the three runs.
COMPAT_FIELDS = [
    "test_set_id",
    "provider",
    "model",
    "configured_num_ctx",
    "timeout_per_question_seconds",
    "neo4j_enabled",
    "clear_neo4j_between_runs",
    "selected_question_count",
]


def load_run(path: Path) -> dict[str, Any]:
    d = json.loads(path.read_text(encoding="utf-8"))
    d["_path"] = str(path)
    return d


def check_compatibility(runs: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    problems: list[str] = []
    for field in COMPAT_FIELDS:
        values = [r.get(field) for r in runs]
        report[field] = values
        if len({json.dumps(v) for v in values}) != 1:
            problems.append(f"{field}: {values}")
    id_sets = [sorted(row["id"] for row in r["results"]) for r in runs]
    if not (id_sets[0] == id_sets[1] == id_sets[2]):
        problems.append("question ID sets differ between runs")
    if any(len(ids) != 50 for ids in id_sets):
        problems.append(f"question counts are {[len(i) for i in id_sets]}, expected 50")
    report["question_ids_identical"] = not any("ID sets" in p for p in problems)
    report["branches_recorded"] = [r.get("branch") for r in runs]
    report["note"] = (
        "Recorded branch names may differ between the official run and the "
        "repeatability branch; inference-implementation equality was verified "
        "externally via `git diff b9608d0 -- src api prompts ...` (clean)."
    )
    if problems:
        raise SystemExit("Incompatible run configurations:\n" + "\n".join(problems))
    return report


def normalized_match(row: dict[str, Any]) -> bool:
    ne, np_ = row.get("normalized_expected"), row.get("normalized_predicted")
    if ne is None or np_ is None:
        return False
    return ne == np_ or ne in np_


def terminal_claim_key(row: dict[str, Any]) -> str:
    tc = row.get("terminal_claim") or {}
    return json.dumps(
        [tc.get("subject"), tc.get("relation"), tc.get("object")], ensure_ascii=False
    )


def label_tuple(row: dict[str, Any]) -> list[int]:
    return [
        int(row.get("final_supported_count") or 0),
        int(row.get("final_contradicted_count") or 0),
        int(row.get("final_no_evidence_count") or 0),
    ]


def run_aggregates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    runtimes = [float(r.get("runtime_seconds") or 0.0) for r in rows]
    iters = [int(r.get("iterations") or 0) for r in rows]
    revs = [int(r.get("revisions") or 0) for r in rows]
    return {
        "completed": sum(1 for r in rows if r.get("terminal_state") == "completed"),
        "errors": sum(1 for r in rows if r.get("error")),
        "timeouts": sum(1 for r in rows if r.get("terminal_state") == "timeout"),
        "exact_match": sum(1 for r in rows if r.get("exact_match")),
        "contains_expected": sum(1 for r in rows if r.get("contains_expected_answer")),
        "normalized_match": sum(1 for r in rows if normalized_match(r)),
        "pipeline_resolved": sum(1 for r in rows if r.get("resolved_by_pipeline")),
        "evidence_path_complete": sum(1 for r in rows if r.get("evidence_path_complete")),
        "iterations_total": sum(iters),
        "iterations_avg": round(statistics.mean(iters), 3),
        "revisions_total": sum(revs),
        "revisions_avg": round(statistics.mean(revs), 3),
        "runtime_mean_s": round(statistics.mean(runtimes), 3),
        "runtime_median_s": round(statistics.median(runtimes), 3),
        "stop_reasons": dict(Counter(str(r.get("final_stop_reason")) for r in rows)),
        "final_labels": {
            "supported": sum(int(r.get("final_supported_count") or 0) for r in rows),
            "contradicted": sum(int(r.get("final_contradicted_count") or 0) for r in rows),
            "no_evidence": sum(int(r.get("final_no_evidence_count") or 0) for r in rows),
        },
    }


def across(vals: list[float]) -> dict[str, float]:
    return {
        "mean": round(statistics.mean(vals), 3),
        "min": min(vals),
        "max": max(vals),
        "range": round(max(vals) - min(vals), 3),
    }


def all_same(values: list[Any]) -> bool:
    return len({json.dumps(v, ensure_ascii=False, sort_keys=True) for v in values}) == 1


def cohens_kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1, pb1 = sum(a) / n, sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe == 1.0:
        return None  # undefined when both raters are constant
    return round((po - pe) / (1 - pe), 3)


def per_question_comparison(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = [{row["id"]: row for row in r["results"]} for r in runs]
    out = []
    for qid in sorted(by_id[0]):
        rows = [m[qid] for m in by_id]
        entry: dict[str, Any] = {
            "id": qid,
            "hop_count": rows[0].get("hop_count"),
            "expected_answer": rows[0].get("expected_answer"),
            "per_run": [
                {
                    "run": RUN_NAMES[i],
                    "execution_id": r.get("execution_id"),
                    "final_answer": r.get("final_answer"),
                    "normalized_predicted": r.get("normalized_predicted"),
                    "exact_match": bool(r.get("exact_match")),
                    "contains_expected": bool(r.get("contains_expected_answer")),
                    "resolved": bool(r.get("resolved_by_pipeline")),
                    "stop_reason": r.get("final_stop_reason"),
                    "path_complete": bool(r.get("evidence_path_complete")),
                    "terminal_claim": r.get("terminal_claim"),
                    "labels_s_c_n": label_tuple(r),
                    "iterations": r.get("iterations"),
                    "revisions": r.get("revisions"),
                }
                for i, r in enumerate(rows)
            ],
        }
        entry["stable"] = {
            "normalized_answer": all_same([r.get("normalized_predicted") for r in rows]),
            "exact_match": all_same([bool(r.get("exact_match")) for r in rows]),
            "contains_expected": all_same(
                [bool(r.get("contains_expected_answer")) for r in rows]
            ),
            "resolved": all_same([bool(r.get("resolved_by_pipeline")) for r in rows]),
            "stop_reason": all_same([r.get("final_stop_reason") for r in rows]),
            "path_complete": all_same([bool(r.get("evidence_path_complete")) for r in rows]),
            "terminal_claim": all_same([terminal_claim_key(r) for r in rows]),
            "label_tuple": all_same([label_tuple(r) for r in rows]),
        }
        out.append(entry)
    return out


def classify(entry: dict[str, Any]) -> tuple[str, list[str]]:
    """Return (primary_category, change_flags) for one question.

    Primary-category precedence (documented): a question whose textual
    correctness changed is categorized correctness_changed; otherwise a
    resolution change wins; otherwise stop reason; otherwise terminal claim;
    otherwise path status; when two or more of those five dimensions changed
    the primary category is multiple_dimensions_changed. Fully stable
    questions get a stable_* category from contains-expected × resolved;
    wording-only variation is answer_wording_changed_but_correctness_stable.
    """
    st = entry["stable"]
    flags: list[str] = []
    if not (st["exact_match"] and st["contains_expected"]):
        flags.append("correctness_changed")
    if not st["resolved"]:
        flags.append("resolution_status_changed")
    if not st["stop_reason"]:
        flags.append("stop_reason_changed")
    if not st["terminal_claim"]:
        flags.append("terminal_claim_changed")
    if not st["path_complete"]:
        flags.append("path_status_changed")
    if not st["normalized_answer"]:
        flags.append("answer_wording_changed")

    core_flags = [f for f in flags if f != "answer_wording_changed"]
    if not core_flags:
        rows = entry["per_run"]
        correct = rows[0]["contains_expected"]
        resolved = rows[0]["resolved"]
        if not st["normalized_answer"]:
            return "answer_wording_changed_but_correctness_stable", flags
        if correct and resolved:
            return "stable_correct_resolved", flags
        if correct and not resolved:
            return "stable_correct_unresolved", flags
        if not correct and resolved:
            return "stable_incorrect_resolved", flags
        return "stable_incorrect_unresolved", flags
    if len(core_flags) > 1:
        return "multiple_dimensions_changed", flags
    return core_flags[0], flags


def pairwise_agreement(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = [{row["id"]: row for row in r["results"]} for r in runs]
    ids = sorted(by_id[0])
    pairs = [(0, 1), (0, 2), (1, 2)]
    out: dict[str, Any] = {}
    for i, j in pairs:
        name = f"{RUN_NAMES[i]}_vs_{RUN_NAMES[j]}"
        a_rows = [by_id[i][q] for q in ids]
        b_rows = [by_id[j][q] for q in ids]

        def agree(fn) -> float:
            return round(
                sum(1 for a, b in zip(a_rows, b_rows) if fn(a) == fn(b)) / len(ids), 3
            )

        exact_a = [bool(r.get("exact_match")) for r in a_rows]
        exact_b = [bool(r.get("exact_match")) for r in b_rows]
        cont_a = [bool(r.get("contains_expected_answer")) for r in a_rows]
        cont_b = [bool(r.get("contains_expected_answer")) for r in b_rows]
        res_a = [bool(r.get("resolved_by_pipeline")) for r in a_rows]
        res_b = [bool(r.get("resolved_by_pipeline")) for r in b_rows]
        path_a = [bool(r.get("evidence_path_complete")) for r in a_rows]
        path_b = [bool(r.get("evidence_path_complete")) for r in b_rows]
        out[name] = {
            "exact_match": agree(lambda r: bool(r.get("exact_match"))),
            "contains_expected": agree(lambda r: bool(r.get("contains_expected_answer"))),
            "resolved": agree(lambda r: bool(r.get("resolved_by_pipeline"))),
            "path_complete": agree(lambda r: bool(r.get("evidence_path_complete"))),
            "stop_reason": agree(lambda r: r.get("final_stop_reason")),
            "normalized_answer": agree(lambda r: r.get("normalized_predicted")),
            "terminal_claim": agree(terminal_claim_key),
            "kappa": {
                "exact_match": cohens_kappa(exact_a, exact_b),
                "contains_expected": cohens_kappa(cont_a, cont_b),
                "resolved": cohens_kappa(res_a, res_b),
                "path_complete": cohens_kappa(path_a, path_b),
            },
            "kappa_note": (
                "Raw agreement is primary; kappa on n=50 with imbalanced "
                "categories can be distorted and is reported for reference only."
            ),
        }
    return out


def depth_variability(runs: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "note": "Each run contains only five questions per designed depth."
    }
    for depth in range(1, 11):
        per_run = []
        for r in runs:
            rows = [x for x in r["results"] if int(x["hop_count"]) == depth]
            per_run.append(
                {
                    "exact": sum(1 for x in rows if x.get("exact_match")),
                    "contains": sum(1 for x in rows if x.get("contains_expected_answer")),
                    "resolved": sum(1 for x in rows if x.get("resolved_by_pipeline")),
                    "path_complete": sum(
                        1 for x in rows if x.get("evidence_path_complete")
                    ),
                }
            )
        out[str(depth)] = {
            "per_run": per_run,
            "resolved_mean_range": across([p["resolved"] for p in per_run]),
            "exact_mean_range": across([p["exact"] for p in per_run]),
        }
    return out


def revision_variability(per_question: list[dict[str, Any]]) -> dict[str, Any]:
    never = revised_all = behavior_changed = 0
    resolved_no_rev_all = sometimes_resolved_after_rev = rev_inconsistent = 0
    for q in per_question:
        revs = [pr["revisions"] or 0 for pr in q["per_run"]]
        resolved = [pr["resolved"] for pr in q["per_run"]]
        revised = [x > 0 for x in revs]
        if not any(revised):
            never += 1
        if all(revised):
            revised_all += 1
        if any(revised) and not all(revised):
            behavior_changed += 1
        if all(not rv and rs for rv, rs in zip(revised, resolved)):
            resolved_no_rev_all += 1
        if any(rv and rs for rv, rs in zip(revised, resolved)):
            sometimes_resolved_after_rev += 1
        revised_outcomes = {rs for rv, rs in zip(revised, resolved) if rv}
        if len(revised_outcomes) > 1:
            rev_inconsistent += 1
    return {
        "never_revised_any_run": never,
        "revised_in_all_three_runs": revised_all,
        "revision_behavior_changed_between_runs": behavior_changed,
        "consistently_resolved_without_revision": resolved_no_rev_all,
        "resolved_after_revision_in_at_least_one_run": sometimes_resolved_after_rev,
        "revised_runs_with_inconsistent_resolution": rev_inconsistent,
        "limitation": (
            "Result rows do not preserve intermediate answers or claim-label "
            "transitions, so whether a specific revision corrected or regressed "
            "an answer cannot be inferred from these files alone."
        ),
    }


def main() -> None:
    argv = sys.argv[1:]
    if len(argv) < 3:
        raise SystemExit(__doc__)
    paths = [Path(p) for p in argv[:3]]
    out_json = Path(argv[3]) if len(argv) > 3 else Path(DEFAULT_OUT_JSON)
    out_md = Path(argv[4]) if len(argv) > 4 else Path(DEFAULT_OUT_MD)

    runs = [load_run(p) for p in paths]
    compat = check_compatibility(runs)

    aggregates = {RUN_NAMES[i]: run_aggregates(r["results"]) for i, r in enumerate(runs)}
    across_runs = {
        key: across([aggregates[rn][key] for rn in RUN_NAMES])
        for key in [
            "exact_match",
            "contains_expected",
            "normalized_match",
            "pipeline_resolved",
            "evidence_path_complete",
            "iterations_total",
            "revisions_total",
            "runtime_mean_s",
            "runtime_median_s",
        ]
    }

    per_question = per_question_comparison(runs)
    for q in per_question:
        primary, flags = classify(q)
        q["primary_category"] = primary
        q["change_flags"] = flags

    stability_counts = {
        dim: sum(1 for q in per_question if q["stable"][dim])
        for dim in [
            "normalized_answer",
            "exact_match",
            "contains_expected",
            "resolved",
            "stop_reason",
            "path_complete",
            "terminal_claim",
            "label_tuple",
        ]
    }
    category_counts = dict(
        Counter(q["primary_category"] for q in per_question).most_common()
    )
    flag_counts = dict(
        Counter(f for q in per_question for f in q["change_flags"]).most_common()
    )

    analysis = {
        "runs": [
            {
                "name": RUN_NAMES[i],
                "path": r["_path"],
                "generated_at": r.get("generated_at"),
                "branch": r.get("branch"),
            }
            for i, r in enumerate(runs)
        ],
        "design_note": (
            "Run 1 is the pre-specified official run; Runs 2 and 3 are "
            "exact-configuration repetitions. The three runs are repeated "
            "measurements of the same 50 questions, not 150 independent "
            "questions, and three runs do not support strong statistical "
            "inference."
        ),
        "configuration_compatibility": compat,
        "per_run_aggregates": aggregates,
        "across_run_mean_min_max_range": across_runs,
        "per_question_stability_counts": stability_counts,
        "primary_category_counts": category_counts,
        "change_flag_counts": flag_counts,
        "pairwise_agreement": pairwise_agreement(runs),
        "depth_variability": depth_variability(runs),
        "revision_variability": revision_variability(per_question),
        "per_question": per_question,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")

    # ---------------- Markdown ----------------
    md: list[str] = [
        "# GraphEval Three-Run Repeatability Analysis",
        "",
        "Run 1 is the pre-specified official experiment; Runs 2 and 3 are",
        "exact-configuration repetitions executed sequentially on the frozen",
        "inference implementation. The three runs are repeated measurements of the",
        "same 50 questions — they are never pooled as 150 independent questions,",
        "and three runs do not support strong statistical inference.",
        "",
        "## Runs",
        "",
        "| Run | File | Generated |",
        "|---|---|---|",
    ]
    for i, r in enumerate(runs):
        md.append(f"| {RUN_NAMES[i]} | `{Path(r['_path']).name}` | {r.get('generated_at')} |")
    md += [
        "",
        "## Per-run aggregates (n=50 each)",
        "",
        "| Metric | Run 1 | Run 2 | Run 3 | Mean | Range |",
        "|---|---|---|---|---|---|",
    ]
    for key, label in [
        ("completed", "Completed"),
        ("errors", "Errors"),
        ("timeouts", "Timeouts"),
        ("exact_match", "Exact match"),
        ("contains_expected", "Contains expected"),
        ("normalized_match", "Normalized match"),
        ("pipeline_resolved", "Pipeline resolved"),
        ("evidence_path_complete", "Path complete"),
        ("iterations_total", "Iterations total"),
        ("revisions_total", "Revisions total"),
        ("runtime_mean_s", "Runtime mean (s)"),
        ("runtime_median_s", "Runtime median (s)"),
    ]:
        vals = [aggregates[rn][key] for rn in RUN_NAMES]
        mean = round(statistics.mean(vals), 2)
        rng = round(max(vals) - min(vals), 2)
        md.append(f"| {label} | {vals[0]} | {vals[1]} | {vals[2]} | {mean} | {rng} |")
    md += ["", "### Stop reasons by run", "", "| Stop reason | Run 1 | Run 2 | Run 3 |", "|---|---|---|---|"]
    reasons = sorted({k for rn in RUN_NAMES for k in aggregates[rn]["stop_reasons"]})
    for reason in reasons:
        md.append(
            "| " + reason + " | "
            + " | ".join(str(aggregates[rn]["stop_reasons"].get(reason, 0)) for rn in RUN_NAMES)
            + " |"
        )
    md += ["", "### Final claim labels by run", "", "| Label | Run 1 | Run 2 | Run 3 |", "|---|---|---|---|"]
    for lab in ["supported", "contradicted", "no_evidence"]:
        md.append(
            f"| {lab.upper()} | "
            + " | ".join(str(aggregates[rn]["final_labels"][lab]) for rn in RUN_NAMES)
            + " |"
        )
    md += [
        "",
        "## Per-question stability across all three runs (n=50 questions)",
        "",
        "| Dimension | Stable in all 3 runs |",
        "|---|---|",
    ]
    for dim, label in [
        ("normalized_answer", "Identical normalized final answer"),
        ("exact_match", "Same exact-match status"),
        ("contains_expected", "Same contains-expected status"),
        ("resolved", "Same resolved/unresolved status"),
        ("stop_reason", "Same stop reason"),
        ("path_complete", "Same evidence-path completeness"),
        ("terminal_claim", "Same terminal claim"),
        ("label_tuple", "Same final label-count tuple"),
    ]:
        md.append(f"| {label} | {stability_counts[dim]}/50 |")
    md += ["", "## Primary stability categories", "", "| Category | Count |", "|---|---|"]
    for cat, count in category_counts.items():
        md.append(f"| {cat} | {count} |")
    md += ["", "Change flags (a question may carry several):", "", "| Flag | Count |", "|---|---|"]
    for flag, count in flag_counts.items():
        md.append(f"| {flag} | {count} |")
    md += [
        "",
        "## Pairwise agreement (fraction of 50 questions agreeing)",
        "",
        "| Dimension | R1 vs R2 | R1 vs R3 | R2 vs R3 |",
        "|---|---|---|---|",
    ]
    pw = analysis["pairwise_agreement"]
    for dim in ["exact_match", "contains_expected", "resolved", "path_complete",
                "stop_reason", "normalized_answer", "terminal_claim"]:
        md.append(
            f"| {dim} | {pw['run1_vs_run2'][dim]} | {pw['run1_vs_run3'][dim]} | {pw['run2_vs_run3'][dim]} |"
        )
    md += [
        "",
        "Cohen's kappa (booleans; reference only — raw agreement is primary because",
        "n = 50 and imbalanced categories can distort kappa):",
        "",
        "| Dimension | R1 vs R2 | R1 vs R3 | R2 vs R3 |",
        "|---|---|---|---|",
    ]
    for dim in ["exact_match", "contains_expected", "resolved", "path_complete"]:
        md.append(
            f"| {dim} | {pw['run1_vs_run2']['kappa'][dim]} | {pw['run1_vs_run3']['kappa'][dim]} | {pw['run2_vs_run3']['kappa'][dim]} |"
        )
    md += [
        "",
        "## Depth-level variability",
        "",
        "Each run contains only five questions per designed depth.",
        "",
        "| Depth | Exact (R1/R2/R3) | Contains (R1/R2/R3) | Resolved (R1/R2/R3) | Path (R1/R2/R3) | Resolved range |",
        "|---|---|---|---|---|---|",
    ]
    dv = analysis["depth_variability"]
    for depth in range(1, 11):
        pr = dv[str(depth)]["per_run"]
        md.append(
            f"| {depth} | "
            + "/".join(str(p["exact"]) for p in pr) + " | "
            + "/".join(str(p["contains"]) for p in pr) + " | "
            + "/".join(str(p["resolved"]) for p in pr) + " | "
            + "/".join(str(p["path_complete"]) for p in pr) + " | "
            + str(dv[str(depth)]["resolved_mean_range"]["range"]) + " |"
        )
    rv = analysis["revision_variability"]
    md += [
        "",
        "## Revision variability",
        "",
        f"- Never revised in any run: {rv['never_revised_any_run']}",
        f"- Revised in all three runs: {rv['revised_in_all_three_runs']}",
        f"- Revision behavior changed between runs: {rv['revision_behavior_changed_between_runs']}",
        f"- Consistently resolved without revision in all runs: {rv['consistently_resolved_without_revision']}",
        f"- Resolved after revision in at least one run: {rv['resolved_after_revision_in_at_least_one_run']}",
        f"- Revised runs with inconsistent resolution outcomes: {rv['revised_runs_with_inconsistent_resolution']}",
        "",
        rv["limitation"],
        "",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")


if __name__ == "__main__":
    main()
