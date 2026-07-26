"""Prove expected answers/paths are not exposed during inference."""

from __future__ import annotations

from pathlib import Path

from src.benchmarks import list_questions, score_result
from src.models import Example

ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "prompts"


def test_benchmark_ui_questions_exclude_scoring_fields():
    rows = list_questions("apollo_multihop_50", hop=1)
    assert rows
    for row in rows:
        assert "expected_answer" not in row
        assert "expected_path" not in row
        assert "expected_paths" not in row


def test_example_has_no_expected_answer_field():
    example = Example(
        id="x",
        question="Where is Host C?",
        context="Host C is located in Rack R7.",
    )
    assert not hasattr(example, "expected_answer")
    assert "expected_answer" not in example.__dict__


def test_prompt_templates_do_not_mention_expected_answer_or_path():
    forbidden = ("expected_answer", "expected_path", "{{expected", "gold_answer")
    for path in PROMPT_DIR.glob("*.txt"):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token.lower() not in text, f"{path.name} contains {token}"


def test_scorer_is_post_inference_only():
    # score_result is the only approved place expected values enter the run path.
    assert callable(score_result)
    source = (ROOT / "src" / "benchmarks" / "catalog.py").read_text(encoding="utf-8")
    assert "def score_result" in source
