"""Approved UI benchmark suites (Apollo + NHS WannaCry only)."""

from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.models import DecomposedBacktrackingResult, SubQuestionStopReason
from src.pipeline.kgc_matching import normalize_entity_text

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "test_sets"

APPROVED_BENCHMARKS: dict[str, Path] = {
    "apollo_multihop_50": DATA_DIR / "apollo_multihop_50.json",
    "nhs_wannacry_multihop_50": DATA_DIR / "nhs_wannacry_multihop_50.json",
}

BENCHMARK_TITLES: dict[str, str] = {
    "apollo_multihop_50": "Apollo Multi-Hop 50",
    "nhs_wannacry_multihop_50": "NHS WannaCry Multi-Hop 50",
}

_UNRESOLVED_STOP_PRIORITY = (
    SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
    SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE,
    SubQuestionStopReason.STALLED,
    SubQuestionStopReason.NO_CLAIMS_EXTRACTED,
    SubQuestionStopReason.GENERATION_FAILED,
    SubQuestionStopReason.MAX_ITERATIONS,
)


def normalize_answer(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def exact_match(predicted: str, expected: str) -> bool:
    return normalize_entity_text(str(predicted)) == normalize_entity_text(str(expected))


def contains_expected_answer(predicted: str, expected: str) -> bool:
    normalized_predicted = normalize_answer(predicted)
    normalized_expected = normalize_answer(expected)
    return bool(
        normalized_expected
        and f" {normalized_expected} " in f" {normalized_predicted} "
    )


def resolved_by_pipeline(result: DecomposedBacktrackingResult) -> bool:
    sub_results = result.sub_question_results
    return bool(sub_results) and all(
        sub.stop_reason == SubQuestionStopReason.RESOLVED for sub in sub_results
    )


def aggregate_stop_reason(
    stops: list[SubQuestionStopReason | str],
) -> str:
    """Single run-level stop reason consistent with pipeline_resolved."""
    if not stops:
        return "NO_SUB_QUESTIONS"

    normalized: list[str] = []
    for stop in stops:
        value = stop.value if hasattr(stop, "value") else str(stop)
        normalized.append(value)

    if all(value == SubQuestionStopReason.RESOLVED.value for value in normalized):
        return SubQuestionStopReason.RESOLVED.value

    if any(value == SubQuestionStopReason.RESOLVED.value for value in normalized):
        return "PARTIALLY_UNRESOLVED"

    for candidate in _UNRESOLVED_STOP_PRIORITY:
        if candidate.value in normalized:
            return candidate.value
    return normalized[-1]


def approved_benchmark_ids() -> list[str]:
    return list(APPROVED_BENCHMARKS)


def is_approved_benchmark(benchmark_id: str) -> bool:
    return benchmark_id in APPROVED_BENCHMARKS


@lru_cache(maxsize=8)
def load_benchmark_payload(benchmark_id: str) -> dict[str, Any]:
    if benchmark_id not in APPROVED_BENCHMARKS:
        raise KeyError(f"Unknown benchmark_id: {benchmark_id}")
    path = APPROVED_BENCHMARKS[benchmark_id]
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark file missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Benchmark payload is not an object: {benchmark_id}")
    return payload


def clear_benchmark_cache() -> None:
    load_benchmark_payload.cache_clear()


def list_benchmarks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for benchmark_id in APPROVED_BENCHMARKS:
        payload = load_benchmark_payload(benchmark_id)
        questions = payload.get("questions") or []
        hop_distribution = Counter(int(item.get("hop_count", 0)) for item in questions)
        rows.append(
            {
                "id": benchmark_id,
                "title": BENCHMARK_TITLES.get(benchmark_id, benchmark_id),
                "domain": payload.get("domain") or "",
                "description": payload.get("description") or "",
                "question_count": len(questions),
                "hop_distribution": {
                    str(hop): hop_distribution[hop] for hop in sorted(hop_distribution)
                },
            }
        )
    return rows


def list_questions(
    benchmark_id: str,
    *,
    hop: int | None = None,
) -> list[dict[str, Any]]:
    payload = load_benchmark_payload(benchmark_id)
    rows: list[dict[str, Any]] = []
    for item in payload.get("questions") or []:
        hop_count = int(item["hop_count"])
        if hop is not None and hop_count != hop:
            continue
        rows.append(
            {
                "id": str(item["id"]),
                "hop_count": hop_count,
                "question": str(item["question"]),
            }
        )
    return rows


def get_question(benchmark_id: str, question_id: str) -> dict[str, Any]:
    payload = load_benchmark_payload(benchmark_id)
    for item in payload.get("questions") or []:
        if str(item.get("id")) == question_id:
            return item
    raise KeyError(f"Question not found: {question_id}")


def trusted_context(benchmark_id: str) -> str:
    payload = load_benchmark_payload(benchmark_id)
    context = str(payload.get("trusted_context") or "").strip()
    if not context:
        raise ValueError(f"Benchmark has empty trusted_context: {benchmark_id}")
    return context


def score_result(
    *,
    benchmark_id: str,
    question: dict[str, Any],
    result: DecomposedBacktrackingResult,
) -> dict[str, Any]:
    expected = str(question.get("expected_answer") or "")
    predicted = str(result.combined_answer or "")
    stops = [sub.stop_reason for sub in result.sub_question_results]
    final_stop = aggregate_stop_reason(stops)
    resolved = resolved_by_pipeline(result)
    if resolved and final_stop != SubQuestionStopReason.RESOLVED.value:
        final_stop = SubQuestionStopReason.RESOLVED.value
    if not resolved and final_stop == SubQuestionStopReason.RESOLVED.value:
        final_stop = "PARTIALLY_UNRESOLVED"
    contains = contains_expected_answer(predicted, expected)
    category = None
    if not resolved:
        if contains:
            category = "answer_matched_textually_but_pipeline_unresolved"
        else:
            stop = str(final_stop or "").casefold()
            if "target_not_satisfied" in stop:
                category = "target_not_satisfied"
            elif "partially_unresolved" in stop:
                category = "pipeline_unresolved"
            elif "no_evidence" in stop:
                category = "unresolved_no_evidence"
            elif "no_claims" in stop:
                category = "no_claims_extracted"
            elif "max_iterations" in stop:
                category = "contradiction_or_uncertainty_remained"
            else:
                category = "pipeline_unresolved"
    return {
        "benchmark_id": benchmark_id,
        "question_id": str(question["id"]),
        "hop_count": int(question["hop_count"]),
        "expected_answer": expected,
        "predicted_answer": predicted,
        "exact_match": exact_match(predicted, expected),
        "contains_expected_answer": contains,
        "resolved_by_pipeline": resolved,
        "final_stop_reason": final_stop,
        "all_stop_reasons": [
            s.value if hasattr(s, "value") else str(s) for s in stops
        ],
        "failure_category": category,
    }
