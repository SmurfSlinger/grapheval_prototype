"""Tests for BenchmarkLock and the new runner flags added in Phase 5–8."""

from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
