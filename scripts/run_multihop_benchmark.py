#!/usr/bin/env python3
"""Run the fixed Apollo multi-hop measurement set without tuning the pipeline."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_lock import BenchmarkLock, BenchmarkLockError
from src.config import DEFAULT_MODEL, NEO4J_ENABLED, OLLAMA_NUM_CTX, PROJECT_ROOT
from src.main import get_provider
from src.models import Example, SubQuestionStopReason
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.storage.neo4j_store import query_relationship_counts_if_enabled


DEFAULT_TEST_SET = PROJECT_ROOT / "data" / "test_sets" / "apollo_multihop_50.json"
DEFAULT_JSON_REPORT = PROJECT_ROOT / "results" / "apollo_multihop_report.json"
DEFAULT_MD_REPORT = PROJECT_ROOT / "results" / "apollo_multihop_summary.md"

# Terminal states recorded in each result row.
TERMINAL_COMPLETED = "completed"
TERMINAL_TIMEOUT = "timeout"
TERMINAL_ERROR = "error"
TERMINAL_INTERRUPTED = "interrupted"


def normalize_answer(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def normalized_match(predicted: str, expected: str) -> bool:
    normalized_predicted = normalize_answer(predicted)
    normalized_expected = normalize_answer(expected)
    return bool(
        normalized_expected
        and (
            normalized_predicted == normalized_expected
            or f" {normalized_expected} " in f" {normalized_predicted} "
        )
    )


def exact_match(predicted: str, expected: str) -> bool:
    return predicted.strip() == expected.strip()


def contains_expected_answer(predicted: str, expected: str) -> bool:
    normalized_predicted = normalize_answer(predicted)
    normalized_expected = normalize_answer(expected)
    return bool(
        normalized_expected
        and f" {normalized_expected} " in f" {normalized_predicted} "
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure decomposed GraphEval performance by designed hop count."
    )
    parser.add_argument("--test-set", type=Path, default=DEFAULT_TEST_SET)
    parser.add_argument("--provider", choices=("mock", "ollama"), default="mock")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--num-ctx",
        type=int,
        default=OLLAMA_NUM_CTX,
        help="Ollama context window passed as options.num_ctx.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--start-at",
        help="Start at this question ID after other selection filters.",
    )
    parser.add_argument(
        "--ids",
        help="Comma-separated question IDs to run in the supplied order.",
    )
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument(
        "--clear-neo4j",
        "--clear-neo4j-between-runs",
        dest="clear_neo4j",
        action="store_true",
        help="Run the visible full local clear before every benchmark question.",
    )
    parser.add_argument(
        "--timeout-per-question",
        type=float,
        default=180.0,
        help="Hard wall-clock limit per question; 0 disables it.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Checkpoint the error and continue instead of stopping.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate benchmark schema and graph paths without loading an LLM.",
    )
    parser.add_argument(
        "--prompt-profile",
        choices=("default", "compact"),
        default="default",
        help="Recorded for comparison; compact currently uses unchanged prompts.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Load existing results from --output and skip completed question IDs. "
            "Preserves prior rows when resuming with --start-at or after interruption."
        ),
    )
    parser.add_argument(
        "--retry-errors",
        "--rerun-errors",
        dest="retry_errors",
        action="store_true",
        help="With --resume, re-run question IDs whose prior row has an error.",
    )
    parser.add_argument(
        "--rerun-completed",
        action="store_true",
        help="With --resume, re-run ALL prior rows including completed ones.",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=float,
        default=0.0,
        help="Seconds to sleep between questions (helps with resource contention).",
    )
    parser.add_argument(
        "--max-consecutive-timeouts",
        type=int,
        default=0,
        help="Stop after this many consecutive timeouts; 0 disables the limit.",
    )
    parser.add_argument(
        "--stop-after-minutes",
        type=float,
        default=0.0,
        help="Stop the run after this many wall-clock minutes; 0 disables it.",
    )
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=None,
        help=(
            "Path for the exclusive run-lock JSON file. "
            "Defaults to .runtime/benchmark.lock under the project root."
        ),
    )
    parser.add_argument(
        "--output",
        "--output-json",
        dest="output_json",
        type=Path,
        default=DEFAULT_JSON_REPORT,
    )
    parser.add_argument(
        "--summary",
        "--output-markdown",
        dest="output_markdown",
        type=Path,
        default=DEFAULT_MD_REPORT,
    )
    return parser.parse_args()


def load_prior_results(path: Path) -> dict[str, dict[str, Any]]:
    """Load prior per-question rows keyed by ID for resumable execution."""
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload.get("results")
    if not isinstance(rows, list):
        return {}
    prior: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("id"):
            prior[str(row["id"])] = row
    return prior


def should_skip_prior_row(
    prior_row: dict[str, Any] | None,
    *,
    resume: bool,
    retry_errors: bool = False,
    rerun_completed: bool = False,
) -> bool:
    if not resume or prior_row is None:
        return False
    if rerun_completed:
        return False
    if retry_errors and prior_row.get("error"):
        return False
    return True


def graph_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    facts = payload["expected_graph_facts"]
    questions = payload["questions"]
    root = payload["root_entity"]
    nodes = {node for subject, _, obj in facts for node in (subject, obj)}
    adjacency: dict[str, set[str]] = defaultdict(set)
    for subject, _, obj in facts:
        adjacency[subject].add(obj)
        adjacency[obj].add(subject)
    components = 0
    unseen = set(nodes)
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            current = stack.pop()
            neighbors = adjacency[current] & unseen
            unseen -= neighbors
            stack.extend(neighbors)
    return {
        "node_count": len(nodes),
        "edge_count": len(facts),
        "connected_components": components,
        "root_node": root,
        "max_designed_hop_depth": max(item["hop_count"] for item in questions),
        "average_expected_hop_count": (
            sum(item["hop_count"] for item in questions) / len(questions)
        ),
        "branching_factor_from_root": len(
            {obj for subject, _, obj in facts if subject == root}
        ),
        "branches_reaching_10_hops": len(
            {
                tuple(item["expected_path"][0])
                for item in questions
                if item["hop_count"] == 10
            }
        ),
    }


def validate_test_set(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    questions = payload.get("questions", [])
    facts_list = payload.get("expected_graph_facts", [])
    facts = {tuple(fact) for fact in facts_list if len(fact) == 3}
    root = payload.get("root_entity")
    trusted_context = str(payload.get("trusted_context", ""))
    required_question_fields = {
        "id",
        "hop_count",
        "question",
        "expected_answer",
        "expected_path",
        "required_entities",
        "required_relations",
    }

    if len(questions) != 50:
        errors.append(f"expected exactly 50 questions, found {len(questions)}")
    counts = Counter(item.get("hop_count") for item in questions)
    expected_counts = {hop: 5 for hop in range(1, 11)}
    if dict(counts) != expected_counts:
        errors.append(f"hop distribution is {dict(counts)}, expected {expected_counts}")
    if len(facts) != len(facts_list):
        errors.append("expected_graph_facts contains duplicate or malformed edges")
    if not trusted_context.strip():
        errors.append("trusted_context is empty")

    seen_ids: set[str] = set()
    ten_hop_branches: set[tuple[str, str, str]] = set()
    for index, item in enumerate(questions, start=1):
        missing = required_question_fields - set(item)
        if missing:
            errors.append(f"question {index} missing fields: {sorted(missing)}")
            continue
        question_id = str(item["id"])
        if question_id in seen_ids:
            errors.append(f"duplicate question id: {question_id}")
        seen_ids.add(question_id)
        path = item["expected_path"]
        hop_count = item["hop_count"]
        if len(path) != hop_count:
            errors.append(
                f"{question_id}: path length {len(path)} != hop_count {hop_count}"
            )
        if not path:
            errors.append(f"{question_id}: expected_path is empty")
            continue
        if path[0][0] != root:
            errors.append(f"{question_id}: path does not start at root {root!r}")
        if any(tuple(edge) not in facts for edge in path):
            errors.append(f"{question_id}: path contains edge absent from graph")
        if any(left[2] != right[0] for left, right in zip(path, path[1:])):
            errors.append(f"{question_id}: expected_path is not contiguous")
        if item["expected_answer"] != path[-1][2]:
            errors.append(f"{question_id}: expected answer is not path terminus")
        path_entities = {
            entity for subject, _, obj in path for entity in (subject, obj)
        }
        path_relations = {relation for _, relation, _ in path}
        if set(item["required_entities"]) != path_entities:
            errors.append(f"{question_id}: required_entities does not match path")
        if set(item["required_relations"]) != path_relations:
            errors.append(f"{question_id}: required_relations does not match path")
        if item["expected_answer"] not in {
            node for subject, _, obj in facts for node in (subject, obj)
        }:
            errors.append(f"{question_id}: expected answer is absent from graph")
        if hop_count == 10:
            ten_hop_branches.add(tuple(path[0]))

    if len(ten_hop_branches) < 2:
        errors.append("fewer than two distinct branches reach 10 hops")
    metrics = graph_metrics(payload) if questions and facts_list else {}
    defined = payload.get("graph_properties", {})
    if defined.get("edge_count_designed") != metrics.get("edge_count"):
        errors.append("declared edge_count_designed does not match graph")
    if defined.get("node_count") != metrics.get("node_count"):
        errors.append("declared node_count does not match graph")
    return {
        "valid": not errors,
        "errors": errors,
        "question_count": len(questions),
        "hop_distribution": dict(sorted(counts.items())),
        "graph_metrics": metrics,
    }


@contextmanager
def question_timeout(seconds: float):
    """Raise TimeoutError when the wall-clock budget for one question expires.

    Implementation note (in-process SIGALRM):
        This context manager arms ``ITIMER_REAL`` / ``SIGALRM`` in the *current*
        process. The Apollo benchmark runner does **not** spawn a child process
        per question, so there is no process group to terminate or reap here.
        When a timeout fires during a blocking Ollama HTTP call, Python raises
        ``TimeoutError`` in this process; any generation already accepted by the
        Ollama *server* may continue server-side until that request ends.

        For owned child processes elsewhere, use
        :func:`terminate_process_group` / :func:`run_subprocess_with_timeout`,
        which send signals to the whole process group and wait/reap.
    """
    if seconds <= 0:
        yield
        return

    def handle_timeout(_signum, _frame):
        raise TimeoutError(f"question exceeded {seconds:g} seconds")

    previous_handler = signal.signal(signal.SIGALRM, handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def terminate_process_group(pid: int, *, grace_seconds: float = 1.0) -> None:
    """Terminate an owned process group and reap the leader.

    Sends SIGTERM to the group, waits briefly, then SIGKILL if still alive,
    and finally ``waitpid`` so the child does not remain a zombie.
    """
    if pid <= 0:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    deadline = time.monotonic() + max(grace_seconds, 0.0)
    while time.monotonic() < deadline:
        try:
            waited_pid, _status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return
        if waited_pid == pid:
            return
        time.sleep(0.05)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass


def run_subprocess_with_timeout(
    args: list[str],
    *,
    timeout_seconds: float,
    grace_seconds: float = 1.0,
) -> subprocess.CompletedProcess[str]:
    """Run a command in a new process group with hard timeout cleanup.

    On timeout the entire process group is terminated and reaped. This helper
    is for owned children; the main benchmark path still uses in-process
    :func:`question_timeout` (see its docstring).
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    proc = subprocess.Popen(
        args,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        terminate_process_group(proc.pid, grace_seconds=grace_seconds)
        raise TimeoutError(
            f"subprocess exceeded {timeout_seconds:g} seconds: {' '.join(args)}"
        ) from exc
    return subprocess.CompletedProcess(
        args=args,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def next_attempt_metadata(
    prior_row: dict[str, Any] | None,
    *,
    resume: bool,
) -> tuple[int, bool]:
    """Return ``(attempt_number, resumed)`` for a question about to execute.

    - Fresh run (no prior row): attempt 1, resumed False
    - Resume/retry of a prior row: attempt = prior attempt_number + 1 (min 2),
      resumed True when ``resume`` is enabled
    """
    if prior_row is None:
        return 1, False
    prior_attempt = prior_row.get("attempt_number")
    try:
        base = int(prior_attempt) if prior_attempt is not None else 1
    except (TypeError, ValueError):
        base = 1
    attempt_number = max(base, 1) + 1
    return attempt_number, bool(resume)


def telemetry_from_calls(
    calls: list[dict[str, Any]],
    configured_num_ctx: int | None,
) -> dict[str, Any]:
    largest = max(calls, key=lambda item: item.get("prompt_characters", 0), default={})
    max_chars = int(largest.get("prompt_characters", 0) or 0)
    approx_tokens = int(largest.get("approx_prompt_tokens", 0) or 0)
    return {
        "llm_call_count": len(calls),
        "max_prompt_characters": max_chars,
        "approx_max_prompt_tokens": approx_tokens,
        "largest_prompt_stage": largest.get("stage"),
        "configured_num_ctx": configured_num_ctx,
        "approached_context_limit": (
            bool(configured_num_ctx)
            and approx_tokens >= int(configured_num_ctx * 0.8)
        ),
    }


def call_telemetry_summary(result, call_start: int) -> dict[str, Any]:
    calls = list(result.trace.llm_call_telemetry[call_start:] if result.trace else [])
    configured_num_ctx = result.trace.configured_num_ctx if result.trace else None
    return telemetry_from_calls(calls, configured_num_ctx)


def configure_neo4j(enabled: bool) -> None:
    """Apply the explicit CLI storage choice to modules with imported constants."""
    import src.config as config_module
    import src.pipeline.decomposed_backtracking_runner as runner_module
    import src.storage.neo4j_store as store_module

    config_module.NEO4J_ENABLED = enabled
    runner_module.NEO4J_ENABLED = enabled
    store_module.NEO4J_ENABLED = enabled


def failure_category(
    *,
    error: str | None,
    resolved_by_pipeline: bool,
    contains_expected: bool,
    final_stop_reason: str | None,
) -> str | None:
    if error:
        lowered = error.casefold()
        if "projection" in lowered:
            return "projection_failure"
        if "timeout" in lowered or "exceeded" in lowered:
            return "model_timeout"
        if "neo4j" in lowered:
            return "neo4j_persistence_or_readback"
        if "context" in lowered and ("large" in lowered or "limit" in lowered):
            return "prompt_or_context_too_large"
        return "pipeline_error"
    if resolved_by_pipeline:
        return None
    if contains_expected:
        return "answer_matched_textually_but_pipeline_unresolved"
    stop = (final_stop_reason or "").casefold()
    if "target_not_satisfied" in stop:
        return "target_not_satisfied"
    if "no_evidence" in stop:
        return "unresolved_no_evidence"
    if "no_claims" in stop:
        return "no_claims_extracted"
    if "max_iterations" in stop:
        return "contradiction_or_uncertainty_remained"
    return "pipeline_unresolved"


def sub_questions_resolved(sub_results: list[Any]) -> bool:
    return bool(sub_results) and all(
        sub.stop_reason == SubQuestionStopReason.RESOLVED
        for sub in sub_results
    )


def base_result_row(
    question: dict[str, Any],
    *,
    provider_name: str,
    model: str,
    num_ctx: int | None,
    attempt_number: int = 1,
    resumed: bool = False,
) -> dict[str, Any]:
    expected = str(question["expected_answer"])
    path = question["expected_path"]
    return {
        "id": question["id"],
        "hop_count": question["hop_count"],
        "question": question["question"],
        "expected_answer": expected,
        "normalized_expected": normalize_answer(expected),
        "predicted_answer": "",
        "normalized_predicted": "",
        "exact_match": False,
        "contains_expected_answer": False,
        "answer_match": False,
        "resolved_by_pipeline": False,
        "final_stop_reason": None,
        "all_stop_reasons": [],
        "final_answer": "",
        "combined_answer": "",
        "iterations": 0,
        "revisions": 0,
        "retries": 0,
        "final_supported_count": 0,
        "final_contradicted_count": 0,
        "final_no_evidence_count": 0,
        "focused_extraction_occurred": False,
        "derived_facts_used": False,
        "neo4j_cleared_before_run": False,
        "fact_edges_written": 0,
        "claim_edges_written": 0,
        "kgc_evaluation_source": "not_run",
        "provider": provider_name,
        "model": model,
        "configured_num_ctx": num_ctx,
        "prompt_telemetry": {
            "llm_call_count": 0,
            "max_prompt_characters": 0,
            "approx_max_prompt_tokens": 0,
            "largest_prompt_stage": None,
            "configured_num_ctx": num_ctx,
            "approached_context_limit": False,
        },
        "max_prompt_characters": 0,
        "approx_max_prompt_tokens": 0,
        "largest_prompt_stage": None,
        "runtime_seconds": 0.0,
        "terminal_state": None,
        "error_type": None,
        "error_message": None,
        "error": None,
        "failure_category": None,
        "attempt_number": attempt_number,
        "resumed": resumed,
        "graph_difficulty": {
            "path_length": len(path),
            "unique_entities_needed": len(set(question["required_entities"])),
            "unique_relations_needed": len(set(question["required_relations"])),
            "requires_alias_resolution": question["requires_alias_resolution"],
            "requires_avoiding_sibling_branches": question[
                "requires_avoiding_sibling_branches"
            ],
            "requires_composed_answer": question["requires_composed_answer"],
            "requires_carry_forward": question["requires_carry_forward"],
        },
    }


def run_one(
    *,
    provider,
    provider_name: str,
    model: str,
    num_ctx: int | None,
    context: str,
    question: dict[str, Any],
    max_iterations: int,
    clear_neo4j: bool,
    neo4j_enabled: bool,
    timeout_seconds: float,
    attempt_number: int = 1,
    resumed: bool = False,
) -> dict[str, Any]:
    started = time.monotonic()
    call_start = len(getattr(provider, "call_telemetry", []))
    row = base_result_row(
        question,
        provider_name=provider_name,
        model=model,
        num_ctx=num_ctx,
        attempt_number=attempt_number,
        resumed=resumed,
    )
    runner = DecomposedBacktrackingRunner(
        provider,
        max_iterations_per_sub_question=max_iterations,
        answer_0_mode="generated_external_projected",
        clear_neo4j_before_run=clear_neo4j,
        neo4j_readback=neo4j_enabled,
        require_neo4j=neo4j_enabled,
    )
    try:
        with question_timeout(timeout_seconds):
            result = runner.run_example(
                Example(
                    id=question["id"],
                    question=question["question"],
                    context=context,
                )
            )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        is_timeout = isinstance(exc, TimeoutError)
        error_calls = list(getattr(provider, "call_telemetry", []))[call_start:]
        telemetry = telemetry_from_calls(error_calls, num_ctx)
        row.update(
            {
                "neo4j_cleared_before_run": (
                    clear_neo4j and "neo4j clear" not in error.casefold()
                ),
                "kgc_evaluation_source": "unknown_due_to_error",
                "prompt_telemetry": telemetry,
                "max_prompt_characters": telemetry["max_prompt_characters"],
                "approx_max_prompt_tokens": telemetry["approx_max_prompt_tokens"],
                "largest_prompt_stage": telemetry["largest_prompt_stage"],
                "runtime_seconds": round(time.monotonic() - started, 3),
                "terminal_state": TERMINAL_TIMEOUT if is_timeout else TERMINAL_ERROR,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "error": error,
                "failure_category": failure_category(
                    error=error,
                    resolved_by_pipeline=False,
                    contains_expected=False,
                    final_stop_reason=None,
                ),
            }
        )
        return row

    final_sub = result.sub_question_results[-1] if result.sub_question_results else None
    predicted = final_sub.final_answer if final_sub else result.combined_answer
    metrics = result.metrics
    histories = [
        item
        for sub_result in result.sub_question_results
        for item in sub_result.iteration_history
    ]
    focused = any(item.focused_enrichment_applied for item in histories)
    derived = any(bool(item.derived_facts_added) for item in histories)
    resolved = sub_questions_resolved(result.sub_question_results)
    expected = str(question["expected_answer"])
    contains = contains_expected_answer(predicted, expected)
    telemetry = call_telemetry_summary(result, call_start)
    counts = query_relationship_counts_if_enabled(
        str(question["id"]),
        required=False,
    ) if neo4j_enabled else None
    final_stop_reason = final_sub.stop_reason.value if final_sub else None
    row.update(
        {
            "predicted_answer": predicted,
            "normalized_predicted": normalize_answer(predicted),
            "exact_match": exact_match(predicted, expected),
            "contains_expected_answer": contains,
            "answer_match": normalized_match(predicted, expected),
            "resolved_by_pipeline": resolved,
            "final_stop_reason": final_stop_reason,
            "all_stop_reasons": [
                sub.stop_reason.value for sub in result.sub_question_results
            ],
            "final_answer": predicted,
            "combined_answer": result.combined_answer,
            "iterations": metrics.total_iterations if metrics else 0,
            "revisions": metrics.total_revisions if metrics else 0,
            "retries": metrics.structured_output_retries if metrics else 0,
            "final_supported_count": metrics.final_supported if metrics else 0,
            "final_contradicted_count": metrics.final_contradicted if metrics else 0,
            "final_no_evidence_count": metrics.final_no_evidence if metrics else 0,
            "focused_extraction_occurred": focused,
            "derived_facts_used": derived,
            "neo4j_cleared_before_run": bool(
                result.trace and result.trace.neo4j_cleared_before_run
            ),
            "fact_edges_written": (counts or {}).get(
                "fact_edges",
                (
                    (result.trace.neo4j_base_facts_persisted or 0)
                    + (result.trace.neo4j_working_facts_persisted or 0)
                    if result.trace
                    else 0
                ),
            ),
            "claim_edges_written": (counts or {}).get("claim_edges", 0),
            "kgc_evaluation_source": (
                result.trace.kgc_evaluation_source if result.trace else "in_memory"
            ),
            "prompt_telemetry": telemetry,
            "max_prompt_characters": telemetry["max_prompt_characters"],
            "approx_max_prompt_tokens": telemetry["approx_max_prompt_tokens"],
            "largest_prompt_stage": telemetry["largest_prompt_stage"],
            "runtime_seconds": round(time.monotonic() - started, 3),
            "terminal_state": TERMINAL_COMPLETED,
            "failure_category": failure_category(
                error=None,
                resolved_by_pipeline=resolved,
                contains_expected=contains,
                final_stop_reason=final_stop_reason,
            ),
        }
    )
    return row


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["hop_count"])].append(row)
    by_hop = {}
    for hop, items in sorted(grouped.items()):
        completed = [item for item in items if not item["error"]]
        failures = Counter(
            item["failure_category"]
            for item in items
            if item["failure_category"]
        )
        by_hop[str(hop)] = {
            "questions": len(items),
            "completed": len(completed),
            "exact_match": sum(bool(item["exact_match"]) for item in items),
            "contains_expected": sum(
                bool(item["contains_expected_answer"]) for item in items
            ),
            "pipeline_resolved": sum(
                bool(item["resolved_by_pipeline"]) for item in items
            ),
            "average_iterations": (
                sum(int(item.get("iterations", 0)) for item in items) / len(items)
            ),
            "average_runtime_seconds": (
                sum(float(item.get("runtime_seconds", 0)) for item in items)
                / len(items)
            ),
            "common_failures": dict(failures.most_common()),
        }
    failures = Counter(
        str(row.get("failure_category"))
        for row in rows
        if row.get("failure_category")
    )
    attempted = len(rows)
    completed = sum(not bool(row["error"]) for row in rows)
    exact = sum(bool(row["exact_match"]) for row in rows)
    contains = sum(bool(row["contains_expected_answer"]) for row in rows)
    resolved = sum(bool(row["resolved_by_pipeline"]) for row in rows)
    return {
        "attempted": attempted,
        "completed": completed,
        "errored": attempted - completed,
        "exact_match_count": exact,
        "exact_match_accuracy": exact / attempted if attempted else 0.0,
        "contains_expected_count": contains,
        "contains_expected_accuracy": contains / attempted if attempted else 0.0,
        "pipeline_resolved_count": resolved,
        "resolved_and_matched_count": sum(
            bool(row["resolved_by_pipeline"])
            and bool(row["contains_expected_answer"])
            for row in rows
        ),
        "unresolved_but_answer_contained_expected_count": sum(
            not bool(row["resolved_by_pipeline"])
            and bool(row["contains_expected_answer"])
            and not bool(row["error"])
            for row in rows
        ),
        "average_iterations": (
            sum(int(row.get("iterations", 0)) for row in rows) / attempted
            if attempted
            else 0.0
        ),
        "average_runtime_seconds": (
            sum(float(row.get("runtime_seconds", 0)) for row in rows) / attempted
            if attempted
            else 0.0
        ),
        "by_hop": by_hop,
        "common_failure_types": dict(failures.most_common()),
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    graph = report["graph_metrics_computed"]
    prompt = report["prompt_context_summary"]
    lines = [
        "# Apollo multi-hop benchmark summary",
        "",
        "This is a measurement report, not a tuned success criterion.",
        "",
        f"- Date/time: `{report['generated_at']}`",
        f"- Branch: `{report['branch']}`",
        f"- Provider/model: `{report['provider']}` / `{report['model']}`",
        f"- Configured num_ctx: `{report['configured_num_ctx']}`",
        f"- Run type: **{report['run_type']}**",
        f"- Attempted/completed/errored: {summary['attempted']} / "
        f"{summary['completed']} / {summary['errored']}",
        f"- Exact-match accuracy: {summary['exact_match_accuracy']:.1%}",
        f"- Contains-expected accuracy: {summary['contains_expected_accuracy']:.1%}",
        f"- Pipeline-resolved count: {summary['pipeline_resolved_count']}",
        f"- Resolved and matched: {summary['resolved_and_matched_count']}",
        "- Unresolved but answer contained expected: "
        f"{summary['unresolved_but_answer_contained_expected_count']}",
        f"- Average iterations: {summary['average_iterations']:.2f}",
        f"- Average runtime: {summary['average_runtime_seconds']:.2f}s",
        "",
        "## Accuracy by hop count",
        "",
        "| Hop count | Questions | Completed | Exact match | Contains expected | "
        "Pipeline resolved | Avg iterations | Avg runtime | Common failures |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for hop, item in report["summary"]["by_hop"].items():
        failures = ", ".join(
            f"{name} ({count})" for name, count in item["common_failures"].items()
        ) or "—"
        lines.append(
            f"| {hop} | {item['questions']} | {item['completed']} | "
            f"{item['exact_match']} | {item['contains_expected']} | "
            f"{item['pipeline_resolved']} | {item['average_iterations']:.2f} | "
            f"{item['average_runtime_seconds']:.2f}s | {failures} |"
        )
    lines.extend(
        [
            "",
            "## Graph properties",
            "",
            f"- Node count: {graph['node_count']}",
            f"- Edge count: {graph['edge_count']}",
            f"- Connected components: {graph['connected_components']}",
            f"- Root node: `{graph['root_node']}`",
            f"- Max designed hop depth: {graph['max_designed_hop_depth']}",
            f"- Root branching factor: {graph['branching_factor_from_root']}",
            f"- Average expected hop count: {graph['average_expected_hop_count']:.1f}",
            f"- Branches reaching 10 hops: {graph['branches_reaching_10_hops']}",
            "",
            "## Prompt/context size",
            "",
            f"- Configured num_ctx: `{prompt['configured_num_ctx']}`",
            f"- Max prompt characters: {prompt['max_prompt_characters']}",
            f"- Approximate max prompt tokens: {prompt['approx_max_prompt_tokens']}",
            f"- Largest prompt stage: `{prompt['largest_prompt_stage']}`",
            f"- Any prompt approached window: {prompt['approached_context_limit']}",
            f"- Recommendation: {prompt['recommendation']}",
            "",
            "## Failure categories",
            "",
        ]
    )
    failures = report["summary"]["common_failure_types"]
    if failures:
        lines.extend(f"- `{name}`: {count}" for name, count in failures.items())
    else:
        lines.append("- None recorded.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Textual answer matching and deterministic pipeline resolution are reported "
            "separately. An answer may contain the expected entity while the pipeline "
            "remains unresolved, or resolve without matching the benchmark answer. "
            "No expected answer is supplied to inference and no pipeline labels are "
            "overridden by this report.",
        ]
    )
    if report["provider"] == "mock":
        summary = report["summary"]
        lines.extend(
            [
                "",
                "## Mock-provider limitation",
                "",
                "This mock run produced "
                f"{summary['attempted']} terminal plumbing records with "
                f"{summary['completed']} successful completions and "
                f"{summary['errored']} projection/pipeline failures. "
                "Those terminal records validate runner checkpointing and "
                "reporting only; they are not model-performance results. "
                "The deterministic mock has no profile for this Apollo context.",
            ]
        )
    return "\n".join(lines) + "\n"


def current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def prompt_context_summary(
    rows: list[dict[str, Any]],
    configured_num_ctx: int | None,
) -> dict[str, Any]:
    largest = max(
        rows,
        key=lambda row: int(row.get("max_prompt_characters", 0)),
        default={},
    )
    max_chars = int(largest.get("max_prompt_characters", 0) or 0)
    approx_tokens = int(largest.get("approx_max_prompt_tokens", 0) or 0)
    approached = bool(
        configured_num_ctx and approx_tokens >= int(configured_num_ctx * 0.8)
    )
    if not max_chars:
        recommendation = (
            "No successful real-provider prompt telemetry was recorded; run a real "
            "smoke before changing context size."
        )
    elif approached:
        recommendation = (
            "Observed prompts approached the configured window; consider a larger "
            "context or a separately validated compact prompt profile."
        )
    else:
        recommendation = (
            "The configured window covered observed prompts; increase it only if later "
            "questions show cutoff evidence and hardware permits."
        )
    return {
        "configured_num_ctx": configured_num_ctx,
        "max_prompt_characters": max_chars,
        "approx_max_prompt_tokens": approx_tokens,
        "largest_prompt_stage": largest.get("largest_prompt_stage"),
        "approached_context_limit": approached,
        "recommendation": recommendation,
    }


def build_report(
    *,
    payload: dict[str, Any],
    validation: dict[str, Any],
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    selected_count: int,
    neo4j_enabled: bool,
) -> dict[str, Any]:
    full_real = (
        args.provider == "ollama"
        and selected_count == len(payload["questions"])
        and len(rows) == len(payload["questions"])
    )
    run_type = (
        "mock_plumbing"
        if args.provider == "mock"
        else "full_real"
        if full_real
        else "partial_real"
    )
    return {
        "test_set_id": payload["test_set_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "branch": current_branch(),
        "run_type": run_type,
        "is_partial": len(rows) < len(payload["questions"]),
        "dataset_question_count": len(payload["questions"]),
        "selected_question_count": selected_count,
        "provider": args.provider,
        "model": args.model,
        "configured_num_ctx": args.num_ctx,
        "prompt_profile": args.prompt_profile,
        "timeout_per_question_seconds": args.timeout_per_question,
        "neo4j_enabled": neo4j_enabled,
        "clear_neo4j_between_runs": args.clear_neo4j,
        "validation": validation,
        "graph_properties_defined": payload["graph_properties"],
        "graph_metrics_computed": graph_metrics(payload),
        "prompt_context_summary": prompt_context_summary(rows, args.num_ctx),
        "summary": summarize(rows),
        "results": rows,
    }


def write_reports(
    report: dict[str, Any],
    *,
    output_json: Path,
    output_markdown: Path,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    output_markdown.write_text(markdown_report(report), encoding="utf-8")


def select_questions(
    questions: list[dict[str, Any]],
    *,
    ids: str | None,
    start_at: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    selected = list(questions)
    by_id = {item["id"]: item for item in questions}
    if ids:
        requested = [item.strip() for item in ids.split(",") if item.strip()]
        unknown = [item for item in requested if item not in by_id]
        if unknown:
            raise ValueError(f"Unknown question IDs: {', '.join(unknown)}")
        selected = [by_id[item] for item in requested]
    if start_at:
        positions = [
            index for index, item in enumerate(selected) if item["id"] == start_at
        ]
        if not positions:
            raise ValueError(f"--start-at ID not selected: {start_at}")
        selected = selected[positions[0] :]
    if limit is not None:
        selected = selected[: max(limit, 0)]
    return selected


def partition_resume_selection(
    questions: list[dict[str, Any]],
    *,
    ids: str | None,
    start_at: str | None,
    limit: int | None,
    resume: bool,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Return report selection and the subset of IDs eligible to execute.

    With ``--resume`` and ``--start-at``, earlier IDs remain in the report when
    prior checkpoint rows exist, while execution starts at ``start_at``.
    """
    report_selection = select_questions(
        questions,
        ids=ids,
        start_at=None if resume else start_at,
        limit=limit,
    )
    if resume and start_at:
        run_selection = select_questions(
            report_selection,
            ids=None,
            start_at=start_at,
            limit=None,
        )
    else:
        run_selection = report_selection
    return report_selection, {str(item["id"]) for item in run_selection}


def main() -> None:
    args = parse_args()
    if args.num_ctx is not None and args.num_ctx <= 0:
        raise SystemExit("--num-ctx must be a positive integer")
    if args.timeout_per_question < 0:
        raise SystemExit("--timeout-per-question cannot be negative")

    payload = json.loads(args.test_set.read_text(encoding="utf-8"))
    validation = validate_test_set(payload)
    if not validation["valid"]:
        print(json.dumps(validation, indent=2))
        raise SystemExit(2)
    if args.validate_only:
        print(json.dumps(validation, indent=2))
        return

    try:
        questions, runnable_ids = partition_resume_selection(
            list(payload["questions"]),
            ids=args.ids,
            start_at=args.start_at,
            limit=args.limit,
            resume=args.resume,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    neo4j_enabled = bool(args.clear_neo4j or NEO4J_ENABLED)
    configure_neo4j(neo4j_enabled)
    if args.num_ctx is not None:
        os.environ["OLLAMA_NUM_CTX"] = str(args.num_ctx)
    provider = get_provider(args.provider, model=args.model, fallback_to_mock=False)
    if hasattr(provider, "num_ctx"):
        provider.num_ctx = args.num_ctx
    # Keep per-call HTTP timeout independent of the whole-question wall clock.
    # Cap only when the question budget is tighter than the provider default.
    if (
        args.timeout_per_question > 0
        and hasattr(provider, "timeout")
        and 0 < args.timeout_per_question < provider.timeout
    ):
        provider.timeout = args.timeout_per_question
    elif hasattr(provider, "timeout") and provider.timeout < 600:
        # CPU local runs need headroom for large structured extractions.
        provider.timeout = max(provider.timeout, 600.0)

    prior_by_id = load_prior_results(args.output_json) if args.resume else {}
    rows: list[dict[str, Any]] = []
    consecutive_timeouts = 0
    run_start = time.monotonic()
    stop_after_seconds = args.stop_after_minutes * 60.0 if args.stop_after_minutes > 0 else 0.0

    lock = BenchmarkLock(
        args.lock_file,
        provider=args.provider,
        model=args.model,
        output_path=str(args.output_json),
    )
    try:
        lock.acquire()
    except BenchmarkLockError as exc:
        raise SystemExit(str(exc)) from exc

    interrupted = False
    try:
        for question in questions:
            # Check wall-clock stop limit.
            if stop_after_seconds > 0 and (time.monotonic() - run_start) >= stop_after_seconds:
                print(f"Stopping: --stop-after-minutes={args.stop_after_minutes} elapsed.")
                break

            question_id = str(question["id"])
            prior_row = prior_by_id.get(question_id)
            executed_now = False
            if question_id not in runnable_ids:
                if prior_row is None:
                    continue
                row = prior_row
                print(
                    f"{row['id']}: kept_prior_before_start_at "
                    f"match={row.get('contains_expected_answer')} "
                    f"resolved={row.get('resolved_by_pipeline')} "
                    f"error={row.get('error') or 'none'}"
                )
            elif should_skip_prior_row(
                prior_row,
                resume=args.resume,
                retry_errors=args.retry_errors,
                rerun_completed=args.rerun_completed,
            ):
                assert prior_row is not None
                row = prior_row
                print(
                    f"{row['id']}: skipped_resume "
                    f"match={row.get('contains_expected_answer')} "
                    f"resolved={row.get('resolved_by_pipeline')} "
                    f"error={row.get('error') or 'none'}"
                )
            else:
                executed_now = True
                attempt_number, resumed = next_attempt_metadata(
                    prior_row,
                    resume=args.resume,
                )
                row = run_one(
                    provider=provider,
                    provider_name=args.provider,
                    model=args.model,
                    num_ctx=args.num_ctx,
                    context=payload["trusted_context"],
                    question=question,
                    max_iterations=args.max_iterations,
                    clear_neo4j=args.clear_neo4j,
                    neo4j_enabled=neo4j_enabled,
                    timeout_seconds=args.timeout_per_question,
                    attempt_number=attempt_number,
                    resumed=resumed,
                )
                print(
                    f"{row['id']}: match={row['contains_expected_answer']} "
                    f"resolved={row['resolved_by_pipeline']} "
                    f"attempt={row['attempt_number']} resumed={row['resumed']} "
                    f"error={row['error'] or 'none'}"
                )
                # Track consecutive timeouts.
                if row.get("terminal_state") == TERMINAL_TIMEOUT:
                    consecutive_timeouts += 1
                else:
                    consecutive_timeouts = 0
            rows.append(row)
            report = build_report(
                payload=payload,
                validation=validation,
                args=args,
                rows=rows,
                selected_count=len(questions),
                neo4j_enabled=neo4j_enabled,
            )
            write_reports(
                report,
                output_json=args.output_json,
                output_markdown=args.output_markdown,
            )
            if executed_now and row.get("error") and not args.continue_on_error:
                break
            if (
                args.max_consecutive_timeouts > 0
                and consecutive_timeouts >= args.max_consecutive_timeouts
            ):
                print(
                    f"Stopping: {consecutive_timeouts} consecutive timeouts "
                    f"reached --max-consecutive-timeouts={args.max_consecutive_timeouts}."
                )
                break
            if executed_now and args.cooldown_seconds > 0:
                time.sleep(args.cooldown_seconds)

    except KeyboardInterrupt:
        interrupted = True
        print("\nInterrupted by user (Ctrl+C).")
    finally:
        lock.release()

    # Mark any executed rows that were not completed as interrupted.
    if interrupted:
        for row in rows:
            if row.get("terminal_state") is None:
                row["terminal_state"] = TERMINAL_INTERRUPTED

    report = build_report(
        payload=payload,
        validation=validation,
        args=args,
        rows=rows,
        selected_count=len(questions),
        neo4j_enabled=neo4j_enabled,
    )
    write_reports(
        report,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
    )
    print(json.dumps(report["summary"], indent=2))
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_markdown}")


if __name__ == "__main__":
    main()
