#!/usr/bin/env python3
"""Presentation-friendly KGc backtracking milestone test report."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["NEO4J_ENABLED"] = "false"

import src.config as config

config.NEO4J_ENABLED = False

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import KgcClaimLabel, KgcEvaluationResult, KgcFact, Triple
from src.pipeline.backtracking_feedback_builder import BacktrackingFeedbackBuilder
from src.pipeline.backtracking_runner import BacktrackingRunner
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_matching import normalize_relation

HYUNDAI = "2018 Hyundai Sonata SE"


def _use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


class Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def bold(self, text: str) -> str:
        return self._wrap("1", text)

    def dim(self, text: str) -> str:
        return self._wrap("2", text)

    def green(self, text: str) -> str:
        return self._wrap("32", text)

    def red(self, text: str) -> str:
        return self._wrap("31", text)

    def cyan(self, text: str) -> str:
        return self._wrap("36", text)


class Report:
    def __init__(self, style: Style) -> None:
        self.style = style
        self.passed = 0
        self.failed = 0

    def section(self, title: str) -> None:
        print()
        print(self.style.bold(title))

    def check_comparator(
        self,
        title: str,
        input_lines: list[str],
        expect: str,
        fn,
    ) -> None:
        self._run(title, input_lines, expect, fn, kind="comparator")

    def check_simple(
        self,
        title: str,
        checks_line: str,
        expect: str,
        fn,
        *,
        result_formatter=None,
    ) -> None:
        self._run(
            title,
            [f"Checks: {checks_line}"],
            expect,
            fn,
            kind="simple",
            result_formatter=result_formatter,
        )

    def _run(self, title, input_lines, expect, fn, kind, result_formatter=None) -> None:
        print()
        try:
            outcome = fn()
            if kind == "comparator":
                result_text = outcome
            elif result_formatter:
                result_text = result_formatter(outcome)
            else:
                result_text = outcome
            print(f"{self.style.green('[PASS]')} {title}")
            for line in input_lines:
                print(self.style.dim(f"  {line}"))
            print(self.style.dim(f"  Expect: {expect}"))
            print(f"  Result: {self.style.green(str(result_text))}")
            self.passed += 1
        except Exception as exc:
            print(f"{self.style.red('[FAIL]')} {title}")
            for line in input_lines:
                print(self.style.dim(f"  {line}"))
            print(self.style.dim(f"  Expect: {expect}"))
            print(f"  Result: {self.style.red(f'FAILED — {exc}')}")
            self.failed += 1

    def summary(self) -> int:
        print()
        if self.failed:
            print(
                self.style.red(
                    f"Summary: {self.passed} passed, {self.failed} failed"
                )
            )
            return 1
        print(self.style.green(f"Summary: {self.passed} passed, 0 failed"))
        return 0


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def _evaluation(label: KgcClaimLabel, relation: str, obj: str) -> KgcEvaluationResult:
    conflicting_fact = None
    conflicting_object = None
    if label == KgcClaimLabel.CONTRADICTED:
        conflicting_object = "Alabama"
        conflicting_fact = KgcFact(
            subject=HYUNDAI,
            relation="assembled_in",
            object="Alabama",
        )
    return KgcEvaluationResult(
        triple=Triple(subject=HYUNDAI, relation=relation, object=obj),
        label=label,
        reason=f"Test reason for {label.value}.",
        evidence="Test evidence.",
        conflicting_object=conflicting_object,
        conflicting_fact=conflicting_fact,
    )


def main() -> int:
    style = Style(_use_color())
    report = Report(style)

    print(style.bold("GraphEval KGc backtracking tests"))
    print(
        style.dim(
            "Verifies: support matching, relation normalization, contradiction detection,"
        )
    )
    print(
        style.dim(
            "          no-evidence detection, backtracking feedback, and end-to-end mock flow"
        )
    )

    report.section("1. Graph comparator")

    def exact_support():
        kgc_facts = [
            KgcFact(
                subject=HYUNDAI,
                relation="has_engine",
                object="2.4L engine",
            )
        ]
        claim = Triple(subject=HYUNDAI, relation="has_engine", object="2.4L engine")
        result = GraphComparator().compare_claims([claim], kgc_facts)[0]
        assert result.label == KgcClaimLabel.SUPPORTED
        return result.label.value

    report.check_comparator(
        "Exact KGc support",
        [
            f"Input:  KGc has ({HYUNDAI}, has_engine, 2.4L engine)",
            "        Answer claims the same fact",
        ],
        "SUPPORTED",
        exact_support,
    )

    def relation_normalization():
        assert normalize_relation("was_assembled_in") == "assembled_in"
        assert normalize_relation("has_engine") == "has_engine"
        kgc_facts = [
            KgcFact(subject=HYUNDAI, relation="assembled_in", object="Alabama")
        ]
        claim = Triple(subject=HYUNDAI, relation="was_assembled_in", object="Alabama")
        result = GraphComparator().compare_claims([claim], kgc_facts)[0]
        assert result.label == KgcClaimLabel.SUPPORTED
        assert "normalization" in result.reason.lower()
        return result.label.value

    report.check_comparator(
        "Relation wording normalization",
        [
            "Input:  KGc relation is assembled_in",
            "        Answer relation is was_assembled_in",
        ],
        "SUPPORTED",
        relation_normalization,
    )

    def contradiction():
        kgc_facts = [
            KgcFact(subject=HYUNDAI, relation="assembled_in", object="Alabama")
        ]
        claim = Triple(subject=HYUNDAI, relation="assembled_in", object="Korea")
        result = GraphComparator().compare_claims([claim], kgc_facts)[0]
        assert result.label == KgcClaimLabel.CONTRADICTED
        assert result.conflicting_object == "Alabama"
        return f"{result.label.value}, conflicting object = {result.conflicting_object}"

    report.check_comparator(
        "Contradiction detection",
        [
            "Input:  KGc says assembled_in = Alabama",
            "        Answer says assembled_in = Korea",
        ],
        "CONTRADICTED, conflicting object = Alabama",
        contradiction,
    )

    def no_evidence():
        kgc_facts = [
            KgcFact(subject=HYUNDAI, relation="assembled_in", object="Alabama")
        ]
        claim = Triple(subject=HYUNDAI, relation="has_turbo", object="true")
        result = GraphComparator().compare_claims([claim], kgc_facts)[0]
        assert result.label == KgcClaimLabel.NO_EVIDENCE
        return result.label.value

    report.check_comparator(
        "No-evidence detection",
        [
            "Input:  Answer claims has_turbo = true",
            "        KGc has no matching support",
        ],
        "NO_EVIDENCE",
        no_evidence,
    )

    report.section("2. Backtracking feedback")

    def supported_feedback():
        feedback = BacktrackingFeedbackBuilder().build(
            [_evaluation(KgcClaimLabel.SUPPORTED, "has_engine", "2.4L engine")]
        )
        assert "preserve" in feedback[0].instruction.lower()
        return "preserve instruction produced"

    report.check_simple(
        "Supported claim feedback",
        "supported claims are preserved",
        "preserve instruction produced",
        supported_feedback,
    )

    def contradicted_feedback():
        feedback = BacktrackingFeedbackBuilder().build(
            [_evaluation(KgcClaimLabel.CONTRADICTED, "assembled_in", "Korea")]
        )
        assert feedback[0].conflicting_object == "Alabama"
        assert "Alabama" in feedback[0].instruction
        assert "kgc" in feedback[0].instruction.lower()
        return "correction instruction includes conflicting object"

    report.check_simple(
        "Contradicted claim feedback",
        "contradicted claims are corrected/removed using KGc",
        "correction instruction includes conflicting object",
        contradicted_feedback,
    )

    def no_evidence_feedback():
        feedback = BacktrackingFeedbackBuilder().build(
            [_evaluation(KgcClaimLabel.NO_EVIDENCE, "has_turbo", "true")]
        )
        instruction = feedback[0].instruction.lower()
        assert "omit" in instruction or "retrieval" in instruction or "adjudication" in instruction
        return "no-evidence instruction produced"

    report.check_simple(
        "No-evidence feedback",
        "unsupported claims are omitted or marked for retrieval/adjudication",
        "no-evidence instruction produced",
        no_evidence_feedback,
    )

    report.section("3. End-to-end mock flows")

    def trace_metadata():
        result = BacktrackingRunner(MockProvider(), max_iterations=1).run_example(
            _example("drone_alpha_7_001")
        )
        payload = result.to_dict()
        assert payload["trace"]["claim_extraction_source"] == "extracted_from_answer_n"
        assert payload["revision_effect"]["preserved_supported_count"] == 1
        no_evidence = next(
            c for c in payload["evaluated_claims"] if c["label"] == "CONTRADICTED"
        )
        assert no_evidence["backtracking_action"]
        return "trace + per-claim metadata exposed"

    report.check_simple(
        "KGc trace metadata",
        "API exposes trace sources and claim-level eval metadata",
        "trace + per-claim metadata exposed",
        trace_metadata,
    )

    def hyundai_flow():
        result = BacktrackingRunner(MockProvider(), max_iterations=1).run_example(
            _example("hyundai_sonata_001")
        )
        assert result.answer_0
        assert result.evaluated_answer == result.answer_0
        assert "has_engine" in {f.relation for f in result.kgc_facts}
        assert "assembled_in" in {f.relation for f in result.kgc_facts}
        assert result.contradicted_count == 2
        assert result.supported_count == 0
        assert result.no_evidence_count == 0
        assert "2.4L engine" in result.answer_1
        assert "Alabama" in result.answer_1
        return result

    report.check_simple(
        "Hyundai KGc flow",
        "Answer(0) -> KGc -> Eval(Answer(0)) -> feedback -> Answer(1)",
        "2 contradicted, 0 supported, revised answer fixes claims",
        hyundai_flow,
        result_formatter=lambda r: (
            f"{r.supported_count} supported, {r.contradicted_count} contradicted, "
            f"{r.no_evidence_count} no evidence\n"
            f"Final answer: contains 2.4L engine and Alabama"
        ),
    )

    def drone_flow():
        result = BacktrackingRunner(MockProvider(), max_iterations=1).run_example(
            _example("drone_alpha_7_001")
        )
        assert result.evaluated_answer == result.answer_0
        assert result.supported_count == 1, (
            "does_not_carry weapons should be SUPPORTED"
        )
        assert result.contradicted_count == 2, (
            "Flight time and recon approval should be CONTRADICTED"
        )
        assert result.no_evidence_count == 0
        relations = {f.relation for f in result.kgc_facts}
        assert "does_not_carry" in relations
        return (
            f"{result.supported_count} supported, {result.contradicted_count} contradicted "
            "(Answer(0) evaluated against KGc)"
        )

    report.check_simple(
        "Drone KGc schema alignment flow",
        "Answer(0) claims evaluated; supported and contradicted labels",
        "1 supported, 2 contradicted",
        drone_flow,
    )

    return report.summary()


if __name__ == "__main__":
    sys.exit(main())
