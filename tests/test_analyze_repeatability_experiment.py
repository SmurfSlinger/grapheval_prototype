"""Tests for scripts/analyze_repeatability_experiment.py using synthetic runs."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyze_repeatability_experiment.py"

spec = importlib.util.spec_from_file_location("analyze_repeatability_experiment", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _row(qid: str, hop: int, **over):
    base = {
        "id": qid,
        "execution_id": f"{qid}__x__{hop}",
        "hop_count": hop,
        "expected_answer": "A",
        "normalized_expected": "a",
        "normalized_predicted": "a",
        "final_answer": "A",
        "exact_match": True,
        "contains_expected_answer": True,
        "resolved_by_pipeline": True,
        "final_stop_reason": "RESOLVED",
        "terminal_state": "completed",
        "error": None,
        "iterations": 1,
        "revisions": 0,
        "runtime_seconds": 40.0,
        "final_supported_count": 1,
        "final_contradicted_count": 0,
        "final_no_evidence_count": 0,
        "evidence_path_complete": True,
        "terminal_claim": {"subject": "S", "relation": "r", "object": "A"},
    }
    base.update(over)
    return base


def _run(rows, **meta):
    payload = {
        "test_set_id": "synthetic",
        "provider": "ollama",
        "model": "llama3.1:8b",
        "configured_num_ctx": 8192,
        "timeout_per_question_seconds": 180.0,
        "neo4j_enabled": True,
        "clear_neo4j_between_runs": True,
        "selected_question_count": len(rows),
        "results": rows,
        "_path": "mem",
    }
    payload.update(meta)
    return payload


def _fifty(mutate=None):
    rows = []
    for i in range(50):
        hop = (i // 5) + 1
        row = _row(f"q{i:03d}", hop)
        if mutate:
            row = mutate(i, row)
        rows.append(row)
    return rows


def test_compatibility_hard_fail_on_model_mismatch():
    r1 = _run(_fifty())
    r2 = _run(_fifty())
    r3 = _run(_fifty(), model="other:7b")
    try:
        mod.check_compatibility([r1, r2, r3])
        raised = False
    except SystemExit:
        raised = True
    assert raised


def test_compatibility_hard_fail_on_id_mismatch():
    rows3 = _fifty()
    rows3[0]["id"] = "q999"
    try:
        mod.check_compatibility([_run(_fifty()), _run(_fifty()), _run(rows3)])
        raised = False
    except SystemExit:
        raised = True
    assert raised


def test_stability_and_categories():
    def mutate3(i, row):
        if i == 0:  # wording changed, correctness stable
            row["normalized_predicted"] = "the a"
            row["final_answer"] = "The A"
        if i == 1:  # resolution changed
            row["resolved_by_pipeline"] = False
            row["final_stop_reason"] = "STALLED"
        if i == 2:  # correctness changed
            row["exact_match"] = False
            row["contains_expected_answer"] = False
            row["normalized_predicted"] = "b"
        return row

    runs = [_run(_fifty()), _run(_fifty()), _run(_fifty(mutate3))]
    pq = mod.per_question_comparison(runs)
    cats = {}
    for q in pq:
        primary, flags = mod.classify(q)
        cats[q["id"]] = (primary, flags)
    assert cats["q000"][0] == "answer_wording_changed_but_correctness_stable"
    # resolution + stop reason changed together -> multiple dimensions
    assert cats["q001"][0] == "multiple_dimensions_changed"
    assert "resolution_status_changed" in cats["q001"][1]
    assert cats["q002"][0] in {"correctness_changed", "multiple_dimensions_changed"}
    assert cats["q010"][0] == "stable_correct_resolved"


def test_pairwise_agreement_perfect():
    runs = [_run(_fifty()), _run(_fifty()), _run(_fifty())]
    pw = mod.pairwise_agreement(runs)
    assert pw["run1_vs_run2"]["exact_match"] == 1.0
    assert pw["run2_vs_run3"]["normalized_answer"] == 1.0
    # kappa undefined when both raters constant
    assert pw["run1_vs_run2"]["kappa"]["exact_match"] is None


def test_end_to_end(tmp_path):
    files = []
    for i in range(3):
        p = tmp_path / f"run{i+1}.json"
        payload = _run(_fifty())
        payload.pop("_path")
        p.write_text(json.dumps(payload))
        files.append(str(p))
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    old = sys.argv
    sys.argv = ["x", *files, str(out_json), str(out_md)]
    try:
        mod.main()
    finally:
        sys.argv = old
    data = json.loads(out_json.read_text())
    assert data["per_question_stability_counts"]["normalized_answer"] == 50
    assert data["primary_category_counts"] == {"stable_correct_resolved": 50}
    assert "Each run contains only five questions per designed depth" in out_md.read_text()


def test_revision_variability():
    def mutate(i, row):
        if i == 0:
            row["revisions"] = 2
        return row

    runs = [_run(_fifty(mutate)), _run(_fifty()), _run(_fifty())]
    pq = mod.per_question_comparison(runs)
    rv = mod.revision_variability(pq)
    assert rv["never_revised_any_run"] == 49
    assert rv["revision_behavior_changed_between_runs"] == 1
    assert rv["revised_in_all_three_runs"] == 0
