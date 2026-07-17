"""Tests for compound question decomposition."""

from __future__ import annotations

import pytest

from src.llm.mock_provider import MockProvider
from src.pipeline.question_splitter import QuestionSplitter
from src.pipeline.structured_output import StructuredOutputError


APOLLO_COMPOUND = (
    "What rocket launched Apollo 11, what engines powered its first stage, "
    "where did it launch from, and what mission goal did it accomplish?"
)


def test_apollo_compound_splits_into_ordered_atomic_questions():
    splitter = QuestionSplitter(MockProvider())
    sub_questions, _retries = splitter.split(APOLLO_COMPOUND)

    assert len(sub_questions) == 4
    assert sub_questions[0].id == 1
    assert "rocket" in sub_questions[0].question.lower()
    assert "engine" in sub_questions[1].question.lower()
    assert "launch" in sub_questions[2].question.lower()
    assert "mission goal" in sub_questions[3].question.lower()


def test_pronoun_resolution_makes_sub_questions_explicit():
    splitter = QuestionSplitter(MockProvider())
    sub_questions, _ = splitter.split(APOLLO_COMPOUND)

    engines_q = sub_questions[1].question.lower()
    assert "apollo 11" in engines_q or "launch vehicle" in engines_q
    assert "its" not in engines_q


def test_apollo_complex_splits_five_sub_questions():
    question = (
        "When was the Apollo 11 mission? Who were the astronauts on the mission? "
        "Where was it launched from? Who was the president at the time? "
        "How much lunar material was collected?"
    )
    sub_questions, _ = QuestionSplitter(MockProvider()).split(question)
    assert len(sub_questions) == 5
    assert sub_questions[2].question.lower().startswith("where was apollo 11")


def test_malformed_question_split_rejected():
    class BadProvider(MockProvider):
        def complete(self, prompt: str) -> str:
            return '{"questions": [{"id": 1}]}'

    with pytest.raises(ValueError, match="Question decomposition failed"):
        QuestionSplitter(BadProvider()).split("Some question?")
