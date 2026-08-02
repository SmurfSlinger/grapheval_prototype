#!/usr/bin/env python3
"""Generate report figures from the final-experiment analysis JSON.

Reads results/research/grapheval_final_experiment_analysis.json (produced by
scripts/analyze_final_experiment.py) so that every plotted number comes from
the authoritative analysis, not manual entry. Writes PNG figures and a
figure_data.json capturing the exact plotted values.

Usage:
    .venv/bin/python scripts/plot_final_experiment.py [analysis_json] [out_dir]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_ANALYSIS = "results/research/grapheval_final_experiment_analysis.json"
DEFAULT_OUT = "results/research/figures"

DEPTH_CAPTION = "Each designed depth contains only five questions; bars are raw counts, not trend estimates."


def main() -> None:
    argv = sys.argv[1:]
    analysis_path = Path(argv[0]) if len(argv) > 0 else Path(DEFAULT_ANALYSIS)
    out_dir = Path(argv[1]) if len(argv) > 1 else Path(DEFAULT_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    by_depth = analysis["by_depth"]
    depths = sorted(by_depth, key=int)
    figure_data: dict[str, object] = {"source_analysis": str(analysis_path)}

    # Figure 1: outcome counts by depth (grouped bars, no trend lines).
    exact = [by_depth[d]["exact_match"] for d in depths]
    contains = [by_depth[d]["contains_expected"] for d in depths]
    resolved = [by_depth[d]["pipeline_resolved"] for d in depths]
    figure_data["fig1_outcomes_by_depth"] = {
        "depths": depths, "exact_match": exact,
        "contains_expected": contains, "pipeline_resolved": resolved,
        "questions_per_depth": 5,
    }
    x = range(len(depths))
    w = 0.27
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar([i - w for i in x], exact, w, label="Exact match", color="#2b6cb0")
    ax.bar(list(x), contains, w, label="Contains expected", color="#68a3d9")
    ax.bar([i + w for i in x], resolved, w, label="Pipeline resolved", color="#c05621")
    ax.set_xticks(list(x), depths)
    ax.set_yticks(range(0, 6))
    ax.set_xlabel("Designed graph-path depth (hops)")
    ax.set_ylabel("Questions (out of 5)")
    ax.set_title("Outcome counts by designed depth — Apollo 50-question run (llama3.1:8b)")
    ax.legend(loc="lower left", fontsize=8)
    fig.text(0.5, -0.02, DEPTH_CAPTION, ha="center", fontsize=8, style="italic")
    fig.tight_layout()
    fig.savefig(out_dir / "fig1_outcomes_by_depth.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # Figure 2: joint textual-correctness x pipeline-resolution outcomes.
    jc = analysis["overall"]["joint_contains_x_resolved"]
    cats = [
        ("textually_correct_and_pipeline_resolved", "Correct &\nresolved"),
        ("textually_correct_but_pipeline_unresolved", "Correct but\nunresolved"),
        ("textually_incorrect_but_pipeline_resolved", "Incorrect but\nresolved"),
        ("textually_incorrect_and_pipeline_unresolved", "Incorrect &\nunresolved"),
    ]
    counts = [jc.get(k, 0) for k, _ in cats]
    figure_data["fig2_joint_outcomes"] = {k: jc.get(k, 0) for k, _ in cats}
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar([lbl for _, lbl in cats], counts,
                  color=["#276749", "#b7791f", "#9b2c2c", "#4a5568"])
    ax.bar_label(bars)
    ax.set_ylabel("Questions (n=50)")
    ax.set_title("Joint textual correctness (contains-expected) × pipeline resolution")
    fig.tight_layout()
    fig.savefig(out_dir / "fig2_joint_outcomes.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # Figure 3: stop-reason distribution.
    stops = analysis["overall"]["stop_reasons"]
    ordered = sorted(stops.items(), key=lambda kv: -kv[1])
    figure_data["fig3_stop_reasons"] = dict(ordered)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    bars = ax.barh([k for k, _ in ordered][::-1], [v for _, v in ordered][::-1],
                   color="#2c5282")
    ax.bar_label(bars)
    ax.set_xlabel("Questions (n=50)")
    ax.set_title("Final stop-reason distribution")
    fig.tight_layout()
    fig.savefig(out_dir / "fig3_stop_reasons.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # Figure 4: first-pass vs revised outcomes.
    rb = analysis["revision_behavior"]
    fp, rv = rb["first_pass_unrevised"], rb["revised_at_least_once"]
    figure_data["fig4_revision_outcomes"] = {"first_pass": fp, "revised": rv}
    labels = ["Count", "Exact", "Contains", "Resolved"]
    fpv = [fp["count"], fp["exact_match"], fp["contains_expected"], fp["pipeline_resolved"]]
    rvv = [rv["count"], rv["exact_match"], rv["contains_expected"], rv["pipeline_resolved"]]
    x = range(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.5, 4))
    b1 = ax.bar([i - w / 2 for i in x], fpv, w, label="First-pass (0 revisions)", color="#276749")
    b2 = ax.bar([i + w / 2 for i in x], rvv, w, label="Revised (≥1 revision)", color="#b7791f")
    ax.bar_label(b1)
    ax.bar_label(b2)
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Questions")
    ax.set_title("Outcomes for first-pass vs revised questions (official run)")
    ax.legend(fontsize=8)
    fig.text(0.5, -0.02,
             "Resolution ends iteration, so first-pass rows are resolved by construction; "
             "revised rows are those the pipeline did not immediately resolve.",
             ha="center", fontsize=8, style="italic")
    fig.tight_layout()
    fig.savefig(out_dir / "fig4_revision_outcomes.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    (out_dir / "figure_data.json").write_text(
        json.dumps(figure_data, indent=2) + "\n", encoding="utf-8"
    )
    for f in sorted(out_dir.iterdir()):
        print("wrote", f)


if __name__ == "__main__":
    main()
