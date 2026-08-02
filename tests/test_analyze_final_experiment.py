"""Tests for scripts/analyze_final_experiment.py.

Uses a small synthetic result payload plus, when present, the authoritative
official result file (asserting the recomputed aggregates equal the runner
summary, which the script itself also enforces).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyze_final_experiment.py"
OFFICIAL = REPO / "results" / "research" / "apollo_multihop_llama31_8b_20260727T203028Z.json"

spec = importlib.util.spec_from_file_location("analyze_final_experiment", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _row(**over):
    base = {
        "id": "q1",
        "execution_id": "q1__x__1",
        "hop_count": 1,
        "exact_match": True,
        "contains_expected_answer": True,
        "answer_match": True,
        "resolved_by_pipeline": True,
        "final_stop_reason": "RESOLVED",
        "terminal_state": "completed",
        "error": None,
        "iterations": 1,
        "revisions": 0,
        "runtime_seconds": 10.0,
        "final_supported_count": 1,
        "final_contradicted_count": 0,
        "final_no_evidence_count": 0,
        "evidence_path_complete": True,
        "evidence_path_length": 1,
        "normalized_expected": "a",
        "normalized_predicted": "a",
        "failure_category": None,
    }
    base.update(over)
    return base


def _payload(rows):
    return {
        "test_set_id": "synthetic",
        "results": rows,
        "summary": {
            "attempted": len(rows),
            "completed": sum(1 for r in rows if r["terminal_state"] == "completed"),
            "errored": sum(1 for r in rows if r["error"]),
            "exact_match_count": sum(1 for r in rows if r["exact_match"]),
            "contains_expected_count": sum(
                1 for r in rows if r["contains_expected_answer"]
            ),
            "pipeline_resolved_count": sum(
                1 for r in rows if r["resolved_by_pipeline"]
            ),
            "resolved_and_matched_count": sum(
                1 for r in rows if r["resolved_by_pipeline"] and r["answer_match"]
            ),
        },
    }


def test_wilson_ci_bounds():
    lo, hi = mod.wilson_ci(27, 50)
    assert 0.0 <= lo < 27 / 50 < hi <= 1.0
    assert mod.wilson_ci(0, 0) == (0.0, 0.0)


def test_joint_categories_partition():
    rows = [
        _row(),
        _row(id="q2", exact_match=False, contains_expected_answer=True,
             resolved_by_pipeline=False, final_stop_reason="STALLED",
             revisions=1, iterations=2, normalized_predicted="b"),
        _row(id="q3", exact_match=False, contains_expected_answer=False,
             resolved_by_pipeline=True, normalized_predicted="b"),
        _row(id="q4", exact_match=False, contains_expected_answer=False,
             resolved_by_pipeline=False, final_stop_reason="UNRESOLVED_NO_EVIDENCE",
             revisions=2, iterations=3, normalized_predicted="b"),
    ]
    b = mod.bucket(rows)
    jc = b["joint_contains_x_resolved"]
    assert jc["textually_correct_and_pipeline_resolved"] == 1
    assert jc["textually_correct_but_pipeline_unresolved"] == 1
    assert jc["textually_incorrect_but_pipeline_resolved"] == 1
    assert jc["textually_incorrect_and_pipeline_unresolved"] == 1
    assert sum(jc.values()) == len(rows)
    assert b["iterations_total"] == 7
    assert b["revisions_total"] == 3


def test_end_to_end_on_synthetic(tmp_path):
    rows = [_row(), _row(id="q2", hop_count=2, exact_match=False,
                         normalized_predicted="b", resolved_by_pipeline=False,
                         final_stop_reason="STALLED", revisions=1, iterations=2)]
    src = tmp_path / "results.json"
    src.write_text(json.dumps(_payload(rows)))
    out_json = tmp_path / "analysis.json"
    out_md = tmp_path / "analysis.md"
    old_argv = sys.argv
    sys.argv = ["analyze_final_experiment.py", str(src), str(out_json), str(out_md)]
    try:
        mod.main()
    finally:
        sys.argv = old_argv
    analysis = json.loads(out_json.read_text())
    assert analysis["overall"]["questions"] == 2
    assert analysis["overall"]["exact_match"] == 1
    assert "1" in analysis["by_depth"] and "2" in analysis["by_depth"]
    assert "Stop-reason distribution" in out_md.read_text()


def test_crosscheck_failure_detected(tmp_path):
    rows = [_row()]
    payload = _payload(rows)
    payload["summary"]["exact_match_count"] = 99  # deliberate drift
    src = tmp_path / "bad.json"
    src.write_text(json.dumps(payload))
    old_argv = sys.argv
    sys.argv = ["x", str(src), str(tmp_path / "o.json"), str(tmp_path / "o.md")]
    try:
        try:
            mod.main()
            raised = False
        except SystemExit:
            raised = True
    finally:
        sys.argv = old_argv
    assert raised


def test_official_run_aggregates_match_summary():
    if not OFFICIAL.exists():
        import pytest

        pytest.skip("official result file not present")
    payload = json.loads(OFFICIAL.read_text())
    rows = payload["results"]
    b = mod.bucket(rows)
    s = payload["summary"]
    assert b["questions"] == s["attempted"] == 50
    assert b["exact_match"] == s["exact_match_count"]
    assert b["contains_expected"] == s["contains_expected_count"]
    assert b["pipeline_resolved"] == s["pipeline_resolved_count"]
    assert b["errors"] == s["errored"]
