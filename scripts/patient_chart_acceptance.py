#!/usr/bin/env python3
"""Acceptance runs for patient_d_314_complex + apollo_complex regression."""

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


def _summarize(result, run_index: int | None = None) -> dict:
    subs = []
    for sub in result.sub_question_results:
        qt = sub.question_target if isinstance(sub.question_target, dict) else (
            sub.question_target.to_dict() if sub.question_target else None
        )
        hist = []
        for h in sub.iteration_history:
            hist.append(
                {
                    "iteration": h.iteration,
                    "answer": h.answer,
                    "claims": [
                        {
                            "triple": f"{c.triple.subject} — {c.triple.relation} → {c.triple.object}",
                            "label": c.label.value,
                        }
                        for c in h.evaluated_claims
                    ],
                    "focused_facts_added": [
                        f"{f.subject} — {f.relation} → {f.object}"
                        for f in h.focused_facts_added
                    ],
                    "derived_facts_added": [
                        f"{f.subject} — {f.relation} → {f.object}"
                        for f in h.derived_facts_added
                    ],
                    "target_satisfied": h.target_satisfied,
                }
            )
        subs.append(
            {
                "id": sub.sub_question_id,
                "question": sub.question,
                "intent": qt.get("intent") if qt else None,
                "canonical_relation": qt.get("canonical_relation") if qt else None,
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
                "iterations": hist,
            }
        )
    resolved = sum(
        1
        for sub in result.sub_question_results
        if sub.stop_reason == SubQuestionStopReason.RESOLVED
    )
    return {
        "run_index": run_index,
        "resolved_sub_questions": resolved,
        "total_sub_questions": len(result.sub_question_results),
        "projection_method": result.trace.projection_method if result.trace else None,
        "projection_faithfulness_passed": (
            result.trace.projection_faithfulness_passed if result.trace else None
        ),
        "structured_output_retries": result.metrics.structured_output_retries
        if result.metrics
        else 0,
        "combined_answer": result.combined_answer,
        "sub_questions": subs,
        "accepted": resolved == len(result.sub_question_results),
    }


def _run_with_retries(runner, example, attempts: int = 3):
    last_exc = None
    for trial in range(attempts):
        try:
            return runner.run_example(example)
        except (KgcExtractionError, ValueError) as exc:
            last_exc = exc
            print(f"  retry {trial + 1}: {exc}", flush=True)
            time.sleep(2)
    raise RuntimeError(f"Run failed after retries: {last_exc}")


def main() -> int:
    try:
        provider = OllamaProvider(model="gemma4:e2b", verify_on_init=True)
    except OllamaError as exc:
        print(f"Ollama unavailable: {exc}", file=sys.stderr)
        return 1

    runner = DecomposedBacktrackingRunner(
        provider,
        max_iterations_per_sub_question=3,
        answer_0_mode="preset_external_projected",
    )

    print("=== Apollo complex regression ===", flush=True)
    apollo = _run_with_retries(runner, _example("apollo_complex"))
    apollo_summary = _summarize(apollo)
    print(
        f"  resolved={apollo_summary['resolved_sub_questions']}/"
        f"{apollo_summary['total_sub_questions']} "
        f"projection={apollo_summary['projection_method']}",
        flush=True,
    )
    for sub in apollo_summary["sub_questions"]:
        print(
            f"    Q{sub['id']}: {sub['stop_reason']} intent={sub['intent']} "
            f"{sub['initial_labels']}->{sub['final_labels']}",
            flush=True,
        )

    print("=== Patient D-314 consecutive acceptance ===", flush=True)
    accepted: list[dict] = []
    attempt = 0
    while len(accepted) < 3:
        attempt += 1
        print(f"Attempt {attempt} (accepted {len(accepted)}/3)...", flush=True)
        result = _run_with_retries(runner, _example("patient_d_314_complex"))
        summary = _summarize(result, len(accepted) + 1)
        print(
            f"  resolved={summary['resolved_sub_questions']}/{summary['total_sub_questions']} "
            f"retries={summary['structured_output_retries']} "
            f"projection={summary['projection_method']}",
            flush=True,
        )
        for sub in summary["sub_questions"]:
            print(
                f"    Q{sub['id']}: {sub['stop_reason']} intent={sub['intent']} "
                f"init={sub['initial_answer']!r} final={sub['final_answer']!r} "
                f"{sub['initial_labels']}->{sub['final_labels']}",
                flush=True,
            )
        if summary["accepted"]:
            accepted.append(summary)
        else:
            print("  Not fully resolved — restarting consecutive count.", flush=True)
            # Keep failing run for diagnosis but reset consecutive streak.
            accepted = []
            # Persist last failure for inspection.
            fail_path = ROOT / "results" / "patient_d_314_last_failure.json"
            fail_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(f"  Wrote failure trace to {fail_path}", flush=True)
            # Stop after a few failures so we can fix root causes.
            if attempt >= 6:
                report = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "apollo_regression": apollo_summary,
                    "patient_accepted_runs": accepted,
                    "stopped_early": True,
                    "last_failure": summary,
                }
                out = ROOT / "results" / "patient_d_314_acceptance.json"
                out.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(f"Wrote partial report {out}")
                return 1

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "ollama",
        "model": "gemma4:e2b",
        "apollo_regression": apollo_summary,
        "patient_accepted_runs": accepted,
    }
    out = ROOT / "results" / "patient_d_314_acceptance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
