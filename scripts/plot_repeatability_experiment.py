#!/usr/bin/env python3
"""Generate repeatability figures from the three-run analysis JSON.

Reads results/research/repeatability/grapheval_repeatability_analysis.json and
writes PNG figures plus figure_data.json under
results/research/repeatability/figures/. Raw counts only; no smoothed trends.

Usage:
    .venv/bin/python scripts/plot_repeatability_experiment.py [analysis_json] [out_dir]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_ANALYSIS = "results/research/repeatability/grapheval_repeatability_analysis.json"
DEFAULT_OUT = "results/research/repeatability/figures"
RUNS = ["run1", "run2", "run3"]
RUN_LABELS = ["Run 1 (official)", "Run 2", "Run 3"]
DEPTH_CAPTION = "Each run contains only five questions per designed depth."


def main() -> None:
    argv = sys.argv[1:]
    analysis_path = Path(argv[0]) if len(argv) > 0 else Path(DEFAULT_ANALYSIS)
    out_dir = Path(argv[1]) if len(argv) > 1 else Path(DEFAULT_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    a = json.loads(analysis_path.read_text(encoding="utf-8"))
    figure_data: dict[str, object] = {"source_analysis": str(analysis_path)}

    # Figure R1: aggregate outcomes by run.
    metrics = [
        ("exact_match", "Exact match"),
        ("contains_expected", "Contains expected"),
        ("pipeline_resolved", "Pipeline resolved"),
        ("evidence_path_complete", "Path complete"),
    ]
    agg = a["per_run_aggregates"]
    figure_data["figR1"] = {m: [agg[r][m] for r in RUNS] for m, _ in metrics}
    x = range(len(metrics))
    w = 0.26
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    colors = ["#2b6cb0", "#68a3d9", "#c05621"]
    for i, run in enumerate(RUNS):
        vals = [agg[run][m] for m, _ in metrics]
        bars = ax.bar([xi + (i - 1) * w for xi in x], vals, w,
                      label=RUN_LABELS[i], color=colors[i])
        ax.bar_label(bars, fontsize=8)
    ax.set_xticks(list(x), [lbl for _, lbl in metrics])
    ax.set_ylabel("Questions (n=50 per run)")
    ax.set_ylim(0, 55)
    ax.set_title("Aggregate outcomes by run — three-run repeatability study")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "figR1_aggregate_outcomes_by_run.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)

    # Figure R2: stable vs variable questions per outcome dimension.
    sc = a["per_question_stability_counts"]
    dims = [
        ("normalized_answer", "Normalized\nanswer"),
        ("exact_match", "Exact\nmatch"),
        ("contains_expected", "Contains\nexpected"),
        ("resolved", "Resolved"),
        ("stop_reason", "Stop\nreason"),
        ("path_complete", "Path\ncomplete"),
        ("terminal_claim", "Terminal\nclaim"),
        ("label_tuple", "Label\ntuple"),
    ]
    stable = [sc[d] for d, _ in dims]
    variable = [50 - v for v in stable]
    figure_data["figR2"] = {d: sc[d] for d, _ in dims}
    fig, ax = plt.subplots(figsize=(9, 4.2))
    b1 = ax.bar([lbl for _, lbl in dims], stable, color="#276749",
                label="Stable in all 3 runs")
    b2 = ax.bar([lbl for _, lbl in dims], variable, bottom=stable,
                color="#b7791f", label="Varied")
    ax.bar_label(b1, label_type="center", color="white", fontsize=8)
    ax.bar_label(b2, label_type="center", fontsize=8)
    ax.set_ylabel("Questions (n=50)")
    ax.set_title("Stable vs variable questions by outcome dimension (3 runs)")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_dir / "figR2_stability_by_dimension.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)

    # Figure R3: per-question resolution pattern across runs.
    pq = a["per_question"]
    patterns: dict[str, int] = {}
    for q in pq:
        key = "".join("R" if pr["resolved"] else "u" for pr in q["per_run"])
        patterns[key] = patterns.get(key, 0) + 1
    ordered = sorted(patterns.items(), key=lambda kv: -kv[1])
    figure_data["figR3_resolution_patterns"] = dict(ordered)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bars = ax.barh([k for k, _ in ordered][::-1], [v for _, v in ordered][::-1],
                   color="#2c5282")
    ax.bar_label(bars)
    ax.set_xlabel("Questions (n=50)")
    ax.set_title("Resolution pattern across runs (R = resolved, u = unresolved; order Run1·Run2·Run3)")
    fig.tight_layout()
    fig.savefig(out_dir / "figR3_resolution_patterns.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)

    # Figure R4: per-depth resolved counts for all three runs.
    dv = a["depth_variability"]
    depths = [str(d) for d in range(1, 11)]
    figure_data["figR4"] = {
        d: [p["resolved"] for p in dv[d]["per_run"]] for d in depths
    }
    x = range(len(depths))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for i, run in enumerate(RUNS):
        vals = [dv[d]["per_run"][i]["resolved"] for d in depths]
        ax.bar([xi + (i - 1) * w for xi in x], vals, w, label=RUN_LABELS[i],
               color=colors[i])
    ax.set_xticks(list(x), depths)
    ax.set_yticks(range(0, 6))
    ax.set_xlabel("Designed graph-path depth (hops)")
    ax.set_ylabel("Resolved (out of 5)")
    ax.set_title("Pipeline-resolved counts by depth, all three runs")
    ax.legend(fontsize=8)
    fig.text(0.5, -0.02, DEPTH_CAPTION, ha="center", fontsize=8, style="italic")
    fig.tight_layout()
    fig.savefig(out_dir / "figR4_resolved_by_depth_all_runs.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)

    (out_dir / "figure_data.json").write_text(
        json.dumps(figure_data, indent=2) + "\n", encoding="utf-8"
    )
    for f in sorted(out_dir.iterdir()):
        print("wrote", f)


if __name__ == "__main__":
    main()
