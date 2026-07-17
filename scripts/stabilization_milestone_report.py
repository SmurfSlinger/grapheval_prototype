#!/usr/bin/env python3
"""Run stabilization verification: 3 decomposed + 1 monolithic apollo_complex."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["NEO4J_ENABLED"] = "false"

import src.config as config

config.NEO4J_ENABLED = False

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.llm.ollama_provider import OllamaError, OllamaProvider
from src.pipeline.backtracking_runner import BacktrackingRunner
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.structured_output import KgcExtractionError


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def _summarize_decomposed(result, run_index: int) -> dict:
    subs = []
    for sub in result.sub_question_results:
        subs.append(
            {
                "id": sub.sub_question_id,
                "question": sub.question,
                "initial_answer": sub.initial_answer,
                "final_answer": sub.final_answer,
                "initial": {
                    "supported": sub.initial_supported,
                    "contradicted": sub.initial_contradicted,
                    "no_evidence": sub.initial_no_evidence,
                },
                "final": {
                    "supported": sub.final_supported,
                    "contradicted": sub.final_contradicted,
                    "no_evidence": sub.final_no_evidence,
                },
                "revision_count": sub.revision_count,
                "stop_reason": sub.stop_reason.value,
                "target_satisfied": sub.question_target_satisfied,
            }
        )
    return {
        "run_index": run_index,
        "projection_method": result.trace.projection_method if result.trace else None,
        "projection_faithfulness_passed": (
            result.trace.projection_faithfulness_passed if result.trace else None
        ),
        "structured_output_retries": result.metrics.structured_output_retries
        if result.metrics
        else 0,
        "resolved_sub_questions": result.metrics.resolved_sub_questions
        if result.metrics
        else 0,
        "combined_answer": result.combined_answer,
        "sub_questions": subs,
    }


def _summarize_monolithic(result) -> dict:
    return {
        "supported": result.supported_count,
        "contradicted": result.contradicted_count,
        "no_evidence": result.no_evidence_count,
        "claims_extracted": len(result.extracted_claims),
        "iterations": result.iteration,
        "final_answer": result.final_answer,
        "initial_answer": result.answer_0,
        "stop_reason": result.stop_reason,
    }


def _run_with_retries(fn, *, attempts: int = 3, pause_s: float = 2.0):
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except KgcExtractionError as exc:
            last_exc = exc
            print(f"  attempt {attempt}/{attempts} failed: {exc}", flush=True)
            if attempt < attempts:
                time.sleep(pause_s)
    assert last_exc is not None
    raise last_exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="ollama", choices=["mock", "ollama"])
    parser.add_argument("--model", default="gemma4:e2b")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--run-attempts", type=int, default=3)
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "stabilization_milestone_report.json"),
    )
    args = parser.parse_args()

    if args.provider == "ollama":
        try:
            provider = OllamaProvider(model=args.model, verify_on_init=True)
        except OllamaError as exc:
            print(f"Ollama unavailable: {exc}", file=sys.stderr)
            return 1
    else:
        provider = MockProvider()

    example = _example("apollo_complex")
    decomposed_runner = DecomposedBacktrackingRunner(
        provider,
        max_iterations_per_sub_question=3,
        answer_0_mode="preset_external_projected",
    )
    monolithic_runner = BacktrackingRunner(provider, max_iterations=3)

    decomposed_runs = []
    for i in range(args.runs):
        print(f"Decomposed run {i + 1}/{args.runs}...", flush=True)

        def _decomposed_run():
            return decomposed_runner.run_example(example)

        result = _run_with_retries(_decomposed_run, attempts=args.run_attempts)
        decomposed_runs.append(_summarize_decomposed(result, i + 1))

    print("Monolithic comparison run...", flush=True)

    def _monolithic_run():
        return monolithic_runner.run_example(example, answer_0_mode="preset")

    mono = _run_with_retries(_monolithic_run, attempts=args.run_attempts)
    monolithic = _summarize_monolithic(mono)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": args.provider,
        "model": args.model if args.provider == "ollama" else "mock",
        "example_id": example.id,
        "decomposed_runs": decomposed_runs,
        "monolithic": monolithic,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")

    for run in decomposed_runs:
        print(
            f"Run {run['run_index']}: projection={run['projection_method']} "
            f"resolved={run['resolved_sub_questions']}/5 "
            f"retries={run['structured_output_retries']}"
        )
    print(
        f"Monolithic: S/C/NE={monolithic['supported']}/{monolithic['contradicted']}/"
        f"{monolithic['no_evidence']} claims={monolithic['claims_extracted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
