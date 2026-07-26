"""Tests for BenchmarkLock and the new runner flags added in Phase 5–8."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# BenchmarkLock tests (Phase 5)
# --------------------------------------------------------------------------

from scripts.benchmark_lock import BenchmarkLock, BenchmarkLockError


def test_lock_acquires_and_creates_file(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    lock = BenchmarkLock(lock_file, provider="mock", model="test-model")
    lock.acquire()
    try:
        assert lock_file.exists()
        payload = json.loads(lock_file.read_text())
        assert payload["pid"] == os.getpid()
        assert payload["provider"] == "mock"
        assert payload["model"] == "test-model"
        assert "timestamp" in payload
        assert "hostname" in payload
    finally:
        lock.release()


def test_lock_release_removes_file(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    lock = BenchmarkLock(lock_file)
    lock.acquire()
    lock.release()
    assert not lock_file.exists()


def test_lock_context_manager_releases_on_success(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    with BenchmarkLock(lock_file):
        assert lock_file.exists()
    assert not lock_file.exists()


def test_lock_context_manager_releases_on_exception(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    try:
        with BenchmarkLock(lock_file):
            assert lock_file.exists()
            raise ValueError("simulated failure")
    except ValueError:
        pass
    assert not lock_file.exists()


def test_second_lock_refused_when_first_is_live(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    first = BenchmarkLock(lock_file)
    first.acquire()
    try:
        second = BenchmarkLock(lock_file)
        with pytest.raises(BenchmarkLockError, match="active"):
            second.acquire()
    finally:
        first.release()


def test_stale_lock_is_cleaned_up(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    # Write a lock file with a PID that is certainly not alive.
    stale_pid = 99999999
    lock_file.write_text(
        json.dumps({"pid": stale_pid, "timestamp": "2020-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    lock = BenchmarkLock(lock_file)
    lock.acquire()  # should not raise
    try:
        assert lock_file.exists()
        payload = json.loads(lock_file.read_text())
        assert payload["pid"] == os.getpid()
    finally:
        lock.release()


def test_malformed_lock_file_fails_safely_without_overwrite(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    lock_file.write_text("{not-json", encoding="utf-8")
    lock = BenchmarkLock(lock_file)
    with pytest.raises(BenchmarkLockError, match="malformed"):
        lock.acquire()
    assert lock_file.read_text(encoding="utf-8") == "{not-json"


def test_unverifiable_pid_fails_safely_without_overwrite(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    original = json.dumps({"pid": "not-a-pid", "timestamp": "2020-01-01T00:00:00+00:00"})
    lock_file.write_text(original, encoding="utf-8")
    lock = BenchmarkLock(lock_file)
    with pytest.raises(BenchmarkLockError, match="unverifiable"):
        lock.acquire()
    assert lock_file.read_text(encoding="utf-8") == original


def test_lock_acquisition_is_atomic_across_separate_processes(tmp_path: Path) -> None:
    lock_file = tmp_path / "atomic.lock"
    result_a = tmp_path / "a.json"
    result_b = tmp_path / "b.json"
    script = f"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r})
from scripts.benchmark_lock import BenchmarkLock, BenchmarkLockError
lock_file = Path({str(lock_file)!r})
out = Path(sys.argv[1])
hold = float(sys.argv[2])
try:
    lock = BenchmarkLock(lock_file)
    lock.acquire()
except BenchmarkLockError as exc:
    out.write_text(json.dumps({{"ok": False, "error": str(exc)}}))
    raise SystemExit(2)
time.sleep(hold)
lock.release()
out.write_text(json.dumps({{"ok": True}}))
"""
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    first = subprocess.Popen(
        [sys.executable, "-c", script, str(result_a), "1.5"],
        env=env,
    )
    time.sleep(0.3)
    second = subprocess.run(
        [sys.executable, "-c", script, str(result_b), "0.1"],
        env=env,
        capture_output=True,
        text=True,
    )
    first_code = first.wait(timeout=10)
    assert first_code == 0
    assert second.returncode == 2
    assert json.loads(result_a.read_text())["ok"] is True
    assert json.loads(result_b.read_text())["ok"] is False
    assert "active" in json.loads(result_b.read_text())["error"]


def test_lock_release_after_keyboard_interrupt(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    lock = BenchmarkLock(lock_file)
    try:
        lock.acquire()
        assert lock_file.exists()
        raise KeyboardInterrupt
    except KeyboardInterrupt:
        lock.release()
    assert not lock_file.exists()


def test_double_release_is_idempotent(tmp_path: Path) -> None:
    lock_file = tmp_path / "test.lock"
    lock = BenchmarkLock(lock_file)
    lock.acquire()
    lock.release()
    lock.release()  # must not raise
    assert not lock_file.exists()


# --------------------------------------------------------------------------
# should_skip_prior_row with new flags (Phase 6)
# --------------------------------------------------------------------------

from scripts.run_multihop_benchmark import should_skip_prior_row


def _make_completed_row() -> dict:
    return {"id": "q1", "error": None, "terminal_state": "completed"}


def _make_error_row() -> dict:
    return {"id": "q1", "error": "TimeoutError: exceeded", "terminal_state": "timeout"}


def test_skip_completed_row_by_default() -> None:
    row = _make_completed_row()
    assert should_skip_prior_row(row, resume=True) is True


def test_skip_error_row_by_default() -> None:
    row = _make_error_row()
    assert should_skip_prior_row(row, resume=True) is True


def test_retry_errors_reruns_error_rows() -> None:
    row = _make_error_row()
    assert should_skip_prior_row(row, resume=True, retry_errors=True) is False


def test_retry_errors_still_skips_completed() -> None:
    row = _make_completed_row()
    assert should_skip_prior_row(row, resume=True, retry_errors=True) is True


def test_rerun_completed_forces_rerun_all() -> None:
    completed = _make_completed_row()
    errored = _make_error_row()
    assert should_skip_prior_row(completed, resume=True, rerun_completed=True) is False
    assert should_skip_prior_row(errored, resume=True, rerun_completed=True) is False


def test_no_resume_never_skips() -> None:
    row = _make_completed_row()
    assert should_skip_prior_row(row, resume=False) is False
    assert should_skip_prior_row(None, resume=True) is False


# --------------------------------------------------------------------------
# attempt_number / resumed persistence across retries
# --------------------------------------------------------------------------

from scripts.run_multihop_benchmark import next_attempt_metadata


def test_next_attempt_metadata_fresh_run() -> None:
    assert next_attempt_metadata(None, resume=False) == (1, False)
    assert next_attempt_metadata(None, resume=True) == (1, False)


def test_next_attempt_metadata_increments_across_resume_retries() -> None:
    first = {"id": "q1", "attempt_number": 1, "resumed": False}
    second_number, second_resumed = next_attempt_metadata(first, resume=True)
    assert second_number == 2
    assert second_resumed is True
    third_number, third_resumed = next_attempt_metadata(
        {"attempt_number": second_number, "resumed": second_resumed},
        resume=True,
    )
    assert third_number == 3
    assert third_resumed is True


def test_next_attempt_metadata_without_resume_flag_still_increments_prior() -> None:
    # Re-running with a prior row present but resume=False still advances the
    # attempt counter when the caller chooses to execute again.
    number, resumed = next_attempt_metadata({"attempt_number": 4}, resume=False)
    assert number == 5
    assert resumed is False


# --------------------------------------------------------------------------
# base_result_row schema (Phase 8)
# --------------------------------------------------------------------------

from scripts.run_multihop_benchmark import base_result_row


def _minimal_question(q_id: str = "test_q", hops: int = 1) -> dict:
    return {
        "id": q_id,
        "hop_count": hops,
        "question": "Who crewed Apollo 11?",
        "expected_answer": "Neil Armstrong",
        "expected_path": [["Apollo 11", "crewed_by", "Neil Armstrong"]],
        "required_entities": ["Apollo 11", "Neil Armstrong"],
        "required_relations": ["crewed_by"],
        "requires_alias_resolution": False,
        "requires_avoiding_sibling_branches": False,
        "requires_composed_answer": False,
        "requires_carry_forward": False,
    }


def test_base_result_row_includes_terminal_state() -> None:
    row = base_result_row(_minimal_question(), provider_name="mock", model="m", num_ctx=None)
    assert "terminal_state" in row
    assert row["terminal_state"] is None


def test_base_result_row_includes_error_type_and_message() -> None:
    row = base_result_row(_minimal_question(), provider_name="mock", model="m", num_ctx=None)
    assert "error_type" in row
    assert "error_message" in row
    assert row["error_type"] is None
    assert row["error_message"] is None


def test_base_result_row_includes_attempt_number() -> None:
    row = base_result_row(
        _minimal_question(), provider_name="mock", model="m", num_ctx=None, attempt_number=2
    )
    assert row["attempt_number"] == 2


def test_base_result_row_includes_resumed_flag() -> None:
    row_fresh = base_result_row(
        _minimal_question(), provider_name="mock", model="m", num_ctx=None
    )
    row_resumed = base_result_row(
        _minimal_question(), provider_name="mock", model="m", num_ctx=None, resumed=True
    )
    assert row_fresh["resumed"] is False
    assert row_resumed["resumed"] is True


# --------------------------------------------------------------------------
# Terminal-state distinction (Phase 8)
# --------------------------------------------------------------------------

from scripts.run_multihop_benchmark import (
    TERMINAL_COMPLETED,
    TERMINAL_ERROR,
    TERMINAL_INTERRUPTED,
    TERMINAL_TIMEOUT,
)


def test_terminal_state_constants_are_distinct() -> None:
    states = {TERMINAL_COMPLETED, TERMINAL_ERROR, TERMINAL_INTERRUPTED, TERMINAL_TIMEOUT}
    assert len(states) == 4


def test_timeout_and_error_have_separate_terminal_states() -> None:
    assert TERMINAL_TIMEOUT != TERMINAL_ERROR
    assert TERMINAL_COMPLETED != TERMINAL_INTERRUPTED


def test_mark_interrupted_rows_only_touches_current_run_rows() -> None:
    from scripts.run_multihop_benchmark import mark_interrupted_rows

    rows = [
        {"id": "legacy_missing_terminal", "terminal_state": None},
        {"id": "current_incomplete", "terminal_state": None},
        {"id": "current_completed", "terminal_state": TERMINAL_COMPLETED},
    ]
    mark_interrupted_rows(rows, {"current_incomplete", "current_completed"})
    assert rows[0]["terminal_state"] is None
    assert rows[1]["terminal_state"] == TERMINAL_INTERRUPTED
    assert rows[2]["terminal_state"] == TERMINAL_COMPLETED


# --------------------------------------------------------------------------
# Owned child-process timeout cleanup
# --------------------------------------------------------------------------

from scripts.run_multihop_benchmark import (
    run_subprocess_with_timeout,
    terminate_process_group,
)


def test_timed_out_child_process_is_no_longer_alive() -> None:
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid = proc.pid
    time.sleep(0.2)
    assert _pid_alive(pid)
    terminate_process_group(pid, grace_seconds=0.3)
    assert not _pid_alive(pid)

    with pytest.raises(TimeoutError, match="exceeded"):
        run_subprocess_with_timeout(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout_seconds=0.4,
            grace_seconds=0.2,
        )


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


# --------------------------------------------------------------------------
# Checkpoint atomic write: write_reports uses tmp + rename
# --------------------------------------------------------------------------

from scripts.run_multihop_benchmark import write_reports


def _minimal_report(rows: list) -> dict:
    return {
        "test_set_id": "test",
        "generated_at": "2024-01-01T00:00:00+00:00",
        "branch": "test",
        "run_type": "mock_plumbing",
        "is_partial": False,
        "dataset_question_count": len(rows),
        "selected_question_count": len(rows),
        "provider": "mock",
        "model": "mock",
        "configured_num_ctx": None,
        "prompt_profile": "default",
        "timeout_per_question_seconds": 0,
        "neo4j_enabled": False,
        "clear_neo4j_between_runs": False,
        "validation": {"valid": True, "errors": []},
        "graph_properties_defined": {},
        "graph_metrics_computed": {
            "node_count": 0,
            "edge_count": 0,
            "connected_components": 0,
            "root_node": "Apollo 11",
            "max_designed_hop_depth": 1,
            "average_expected_hop_count": 1.0,
            "branching_factor_from_root": 0,
            "branches_reaching_10_hops": 0,
        },
        "prompt_context_summary": {
            "configured_num_ctx": None,
            "max_prompt_characters": 0,
            "approx_max_prompt_tokens": 0,
            "largest_prompt_stage": None,
            "approached_context_limit": False,
            "recommendation": "No data.",
        },
        "summary": {
            "attempted": len(rows),
            "completed": len(rows),
            "errored": 0,
            "exact_match_count": 0,
            "exact_match_accuracy": 0.0,
            "contains_expected_count": 0,
            "contains_expected_accuracy": 0.0,
            "pipeline_resolved_count": 0,
            "resolved_and_matched_count": 0,
            "unresolved_but_answer_contained_expected_count": 0,
            "average_iterations": 0.0,
            "average_runtime_seconds": 0.0,
            "by_hop": {},
            "common_failure_types": {},
        },
        "results": rows,
    }


def test_write_reports_creates_json_and_markdown(tmp_path: Path) -> None:
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    report = _minimal_report([])
    write_reports(report, output_json=json_path, output_markdown=md_path)
    assert json_path.exists()
    assert md_path.exists()
    parsed = json.loads(json_path.read_text())
    assert parsed["test_set_id"] == "test"


def test_mock_markdown_states_zero_successful_completions() -> None:
    from scripts.run_multihop_benchmark import markdown_report

    report = _minimal_report([])
    report["summary"].update(
        {
            "attempted": 50,
            "completed": 0,
            "errored": 50,
            "common_failure_types": {"projection_failure": 50},
        }
    )
    text = markdown_report(report)
    assert "50 terminal plumbing records" in text
    assert "0 successful completions" in text
    assert "50 projection/pipeline failures" in text
