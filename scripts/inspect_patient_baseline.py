#!/usr/bin/env python3
"""Baseline inspection of patient_d_314_complex on decomposed iterative KGc."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["NEO4J_ENABLED"] = "false"

import src.config as config

config.NEO4J_ENABLED = False

from src.io_utils import load_examples
from src.llm.ollama_provider import OllamaError, OllamaProvider
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.labeled_field_projection import parse_labeled_fields, project_labeled_fields
from src.pipeline.question_splitter import QuestionSplitter
from src.pipeline.question_target import derive_question_target
from src.pipeline.sub_answer_projector import SubAnswerProjector


def main() -> int:
    example = next(ex for ex in load_examples() if ex.id == "patient_d_314_complex")
    print("=== Example loaded ===")
    print("id:", example.id)

    fields = parse_labeled_fields(example.initial_answer)
    print("\n=== Labeled fields ===")
    for label, value in fields:
        print(f"  {label}: {value}")

    try:
        provider = OllamaProvider(model="gemma4:e2b", verify_on_init=True)
    except OllamaError as exc:
        print(f"Ollama unavailable: {exc}", file=sys.stderr)
        return 1

    splitter = QuestionSplitter(provider)
    sub_questions, _split_retries = splitter.split(example.question)
    print("\n=== Decomposition ===")
    for sq in sub_questions:
        print(f"  Q{sq.id}: {sq.question}")
        target = derive_question_target(sq.question, [])
        print(
            f"      intent={target.intent} canonical={target.canonical_relation} "
            f"expected={sorted(target.expected_relations)[:6]}"
        )

    projected = project_labeled_fields(example.initial_answer, sub_questions)
    print("\n=== Deterministic projection ===")
    if projected is None:
        print("  FAILED field-count match; falling back to projector")
        proj = SubAnswerProjector(provider).project(
            example.initial_answer, sub_questions, example.question
        )
        print("  method:", proj.method)
        for item in proj.answers:
            print(f"  Q{item.sub_question_id}: {item.answer}")
    else:
        print("  method: deterministic_labeled_fields")
        for item in projected:
            print(f"  Q{item.sub_question_id}: {item.answer}")

    print("\n=== Full decomposed run ===")
    runner = DecomposedBacktrackingRunner(
        provider,
        max_iterations_per_sub_question=3,
        answer_0_mode="preset_external_projected",
    )
    result = runner.run_example(example)
    summary = []
    for sub in result.sub_question_results:
        hist0 = sub.iteration_history[0] if sub.iteration_history else None
        summary.append(
            {
                "id": sub.sub_question_id,
                "question": sub.question,
                "initial_answer": sub.initial_answer,
                "final_answer": sub.final_answer,
                "stop_reason": sub.stop_reason.value,
                "target_satisfied": sub.question_target_satisfied,
                "target": sub.question_target.to_dict() if sub.question_target else None,
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
                "claims0": [
                    {
                        "triple": f"{c.triple.subject} — {c.triple.relation} → {c.triple.object}",
                        "label": c.label.value,
                    }
                    for c in (hist0.evaluated_claims if hist0 else [])
                ],
                "facts_added": [
                    f"{a.fact.subject} — {a.fact.relation} → {a.fact.object} [{a.provenance}]"
                    for h in sub.iteration_history
                    for a in h.facts_added
                ],
                "derived": [
                    f"{a.fact.subject} — {a.fact.relation} → {a.fact.object}"
                    for h in sub.iteration_history
                    for a in h.derived_facts_added
                ],
            }
        )
        print(
            f"Q{sub.sub_question_id}: {sub.stop_reason.value} "
            f"target={sub.question_target_satisfied} "
            f"intent={(sub.question_target.intent if sub.question_target else None)} "
            f"labels={summary[-1]['initial_labels']}->{summary[-1]['final_labels']}"
        )
        for claim in summary[-1]["claims0"]:
            print(f"    {claim['label']}: {claim['triple']}")

    out = ROOT / "results" / "patient_d_314_baseline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
