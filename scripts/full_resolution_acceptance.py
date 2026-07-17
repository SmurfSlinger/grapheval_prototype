#!/usr/bin/env python3
"""Run consecutive Ollama acceptance trials for apollo_complex 5/5 resolution."""

from __future__ import annotations

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
from src.llm.ollama_provider import OllamaError, OllamaProvider
from src.models import SubQuestionStopReason
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.structured_output import KgcExtractionError


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def _summarize_run(result, run_index: int) -> dict:
    subs = []
    for sub in result.sub_question_results:
        derivation_trace = None
        derived_facts = []
        for h in sub.iteration_history:
            if h.derivation_trace:
                derivation_trace = h.derivation_trace
            derived_facts.extend(h.derived_facts_added)
        subs.append(
            {
                "id": sub.sub_question_id,
                "question": sub.question,
                "initial_answer": sub.initial_answer,
                "final_answer": sub.final_answer,
                "initial_labels": [
                    sub.initial_supported,
                    sub.initial_contradicted,
                    sub.initial_no_evidence,
                ],
                "final_labels": [
                    sub.final_supported,
                    sub.final_contradicted,
                    sub.final_no_evidence,
                ],
                "revision_count": sub.revision_count,
                "stop_reason": sub.stop_reason.value,
                "target_satisfied": sub.question_target_satisfied,
                "derivation_trace": derivation_trace,
                "derived_facts": [f.object for f in derived_facts],
            }
        )
    resolved = sum(
        1 for sub in result.sub_question_results
        if sub.stop_reason == SubQuestionStopReason.RESOLVED
    )
    return {
        "run_index": run_index,
        "resolved_sub_questions": resolved,
        "projection_method": result.trace.projection_method if result.trace else None,
        "projection_faithfulness_passed": (
            result.trace.projection_faithfulness_passed if result.trace else None
        ),
        "structured_output_retries": result.metrics.structured_output_retries
        if result.metrics
        else 0,
        "combined_answer": result.combined_answer,
        "sub_questions": subs,
        "accepted": resolved == 5,
    }


def main() -> int:
    target_runs = 3
    try:
        provider = OllamaProvider(model="gemma4:e2b", verify_on_init=True)
    except OllamaError as exc:
        print(f"Ollama unavailable: {exc}", file=sys.stderr)
        return 1

    example = _example("apollo_complex")
    runner = DecomposedBacktrackingRunner(
        provider,
        max_iterations_per_sub_question=3,
        answer_0_mode="preset_external_projected",
    )

    accepted_runs: list[dict] = []
    attempt = 0
    while len(accepted_runs) < target_runs:
        attempt += 1
        print(f"Attempt {attempt} (accepted {len(accepted_runs)}/{target_runs})...", flush=True)
        for trial in range(3):
            try:
                result = runner.run_example(example)
                break
            except KgcExtractionError as exc:
                print(f"  extraction retry {trial + 1}: {exc}", flush=True)
                time.sleep(2)
        else:
            print("Run failed after extraction retries.", flush=True)
            return 1

        summary = _summarize_run(result, len(accepted_runs) + 1)
        print(
            f"  resolved={summary['resolved_sub_questions']}/5 "
            f"retries={summary['structured_output_retries']}",
            flush=True,
        )
        for sub in summary["sub_questions"]:
            print(
                f"    Q{sub['id']}: {sub['stop_reason']} "
                f"target={sub['target_satisfied']} "
                f"initial={sub['initial_labels']} final={sub['final_labels']}",
                flush=True,
            )

        if summary["accepted"]:
            accepted_runs.append(summary)
        else:
            print("  Not 5/5 — restarting consecutive count.", flush=True)
            accepted_runs = []

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "ollama",
        "model": "gemma4:e2b",
        "example_id": example.id,
        "accepted_runs": accepted_runs,
    }
    out = ROOT / "results" / "full_resolution_acceptance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
