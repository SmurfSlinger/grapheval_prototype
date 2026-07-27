"""Regression tests for atomic decomposition, stall, aggregate status, punctuation."""

from __future__ import annotations

import json

import pytest

from src.benchmarks.catalog import aggregate_stop_reason, exact_match, score_result
from src.llm.mock_provider import MockProvider
from src.models import (
    DecomposedBacktrackingResult,
    SubQuestion,
    SubQuestionResult,
    SubQuestionStopReason,
)
from src.pipeline.kgc_iteration import determine_stop_reason, normalize_answer_text
from src.pipeline.kgc_matching import normalize_entity_text
from src.pipeline.question_decomposition_validation import (
    decomposition_is_valid,
    is_meaningful_subquestion,
)
from src.pipeline.question_splitter import QuestionSplitter
from src.pipeline.structured_triple_validation import coerce_raw_triple_item
from src.pipeline.sub_answer_combiner import combine_sub_answers


class ScriptedSplitProvider(MockProvider):
    def __init__(self, payload: dict) -> None:
        super().__init__()
        self._payload = payload

    def complete(self, prompt: str) -> str:
        if "Compound question:" in prompt or "questions" in prompt.lower():
            return json.dumps(self._payload)
        return super().complete(prompt)


def test_atomic_who_question_remains_one_subquestion():
    question = "Who crewed Apollo 11?"
    # Model returns the invalid token list from the live defect.
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "Who"},
                {"id": 2, "question": "crewed"},
                {"id": 3, "question": "Apollo 11"},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(question)
    assert len(subs) == 1
    assert subs[0].question == question


def test_atomic_what_question_remains_one_subquestion():
    question = "What rocket launched Apollo 11?"
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "What"},
                {"id": 2, "question": "rocket"},
                {"id": 3, "question": "Apollo 11"},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(question)
    assert len(subs) == 1
    assert subs[0].question == question


def test_atomic_where_question_remains_one_subquestion():
    question = "Where was Apollo 11 launched from?"
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "Where"},
                {"id": 2, "question": "launched"},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(question)
    assert len(subs) == 1
    assert subs[0].question == question


def test_malformed_token_list_falls_back_to_original():
    original = "Who crewed Apollo 11?"
    assert not decomposition_is_valid(original, ["Who", "crewed", "Apollo 11"])
    subs, _ = QuestionSplitter(
        ScriptedSplitProvider(
            {
                "questions": [
                    {"id": 1, "question": "Who"},
                    {"id": 2, "question": "crewed"},
                    {"id": 3, "question": "Apollo 11"},
                ]
            }
        )
    ).split(original)
    assert [sq.question for sq in subs] == [original]


def test_atomic_over_split_into_complete_questions_falls_back():
    original = "Who crewed Apollo 11?"
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "Who crewed Apollo 11?"},
                {"id": 2, "question": "Who was Neil Armstrong?"},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(original)
    assert [sq.question for sq in subs] == [original]


def test_empty_decomposition_falls_back_to_original():
    original = "Who crewed Apollo 11?"
    class EmptyProvider(MockProvider):
        def complete(self, prompt: str) -> str:
            return '{"questions": []}'

    subs, _ = QuestionSplitter(EmptyProvider()).split(original)
    assert len(subs) == 1
    assert subs[0].question == original


def test_valid_compound_still_decomposes_into_complete_questions():
    question = "Who crewed Apollo 11, and where was that person born?"
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "Who crewed Apollo 11?"},
                {"id": 2, "question": "Where was Neil Armstrong born?"},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(question)
    assert len(subs) == 2
    assert all(is_meaningful_subquestion(sq.question) for sq in subs)
    assert "Who" not in [sq.question for sq in subs]
    assert "crewed" not in [sq.question for sq in subs]
    assert "Apollo 11" not in [sq.question for sq in subs]


def test_valid_nested_multihop_not_reduced_to_tokens():
    question = (
        "In which town was the Apollo 11 crew member Neil Armstrong born?"
    )
    # Token-list split must fall back to the full nested question.
    token_provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "In"},
                {"id": 2, "question": "which"},
                {"id": 3, "question": "town"},
            ]
        }
    )
    token_subs, _ = QuestionSplitter(token_provider).split(question)
    assert [sq.question for sq in token_subs] == [question]

    # Over-split into complete questions also falls back: nested single-clause
    # multihop stays one sub-question (KG hops are not surface compounds).
    over_split_provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "Who was an Apollo 11 crew member?"},
                {"id": 2, "question": "Where was Neil Armstrong born?"},
            ]
        }
    )
    subs, _ = QuestionSplitter(over_split_provider).split(question)
    assert [sq.question for sq in subs] == [question]
    assert is_meaningful_subquestion(subs[0].question)


def test_identical_supported_answer_states_do_not_need_another_revision():
    stop, detail = determine_stop_reason(
        iteration=1,
        max_iterations=3,
        current_answer="Neil Armstrong.",
        previous_answer="Neil Armstrong",
        previous_signature="SUPPORTED|apollo 11|crewed_by|neil armstrong",
        current_signature="SUPPORTED|apollo 11|crewed_by|neil armstrong",
        supported_count=1,
        contradicted_count=0,
        no_evidence_count=0,
        claim_count=1,
        target_satisfied=False,
        supported_but_irrelevant_count=1,
        new_facts_added=False,
    )
    assert stop == SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED
    assert detail == "unchanged_supported_target_unsatisfied"


def test_aggregate_unresolved_status_cannot_report_resolved():
    stops = [
        SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
        SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
        SubQuestionStopReason.RESOLVED,
    ]
    assert aggregate_stop_reason(stops) == "PARTIALLY_UNRESOLVED"

    result = DecomposedBacktrackingResult(
        example_id="x",
        original_question="Who crewed Apollo 11?",
        context="ctx",
        sub_questions=[
            SubQuestion(id=1, question="Who"),
            SubQuestion(id=2, question="crewed"),
            SubQuestion(id=3, question="Apollo 11"),
        ],
        sub_question_results=[
            SubQuestionResult(
                sub_question_id=1,
                question="Who",
                initial_answer="Neil Armstrong.",
                final_answer="Neil Armstrong.",
                stop_reason=SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
                iteration_count=3,
            ),
            SubQuestionResult(
                sub_question_id=2,
                question="crewed",
                initial_answer="Neil Armstrong.",
                final_answer="Neil Armstrong.",
                stop_reason=SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
                iteration_count=3,
            ),
            SubQuestionResult(
                sub_question_id=3,
                question="Apollo 11",
                initial_answer="Neil Armstrong.",
                final_answer="Neil Armstrong.",
                stop_reason=SubQuestionStopReason.RESOLVED,
                iteration_count=1,
            ),
        ],
        combined_answer="partial",
    )
    score = score_result(
        benchmark_id="apollo_multihop_50",
        question={
            "id": "apollo_hop_001",
            "hop_count": 1,
            "expected_answer": "Neil Armstrong",
        },
        result=result,
    )
    assert score["resolved_by_pipeline"] is False
    assert score["final_stop_reason"] == "PARTIALLY_UNRESOLVED"
    assert score["final_stop_reason"] != "RESOLVED"


def test_harmless_terminal_period_normalization():
    assert normalize_entity_text("Neil Armstrong.") == "Neil Armstrong"
    assert normalize_answer_text("Neil Armstrong.") == "Neil Armstrong"
    triple, anomaly = coerce_raw_triple_item(
        {
            "subject": "Apollo 11",
            "relation": "was_crewed_by",
            "object": "Neil Armstrong.",
        }
    )
    assert anomaly is None
    assert triple is not None
    assert triple.object == "Neil Armstrong"
    assert exact_match("Neil Armstrong.", "Neil Armstrong")


def test_meaningful_punctuation_remains_intact():
    assert normalize_entity_text("Washington, D.C.") == "Washington, D.C."
    assert normalize_entity_text("John F. Kennedy") == "John F. Kennedy"
    assert normalize_entity_text("7.5 kg") == "7.5 kg"
    triple, anomaly = coerce_raw_triple_item(
        {
            "subject": "United States",
            "relation": "has_capital_in",
            "object": "Washington, D.C.",
        }
    )
    assert anomaly is None
    assert triple is not None
    assert triple.object == "Washington, D.C."


def test_single_resolved_combined_answer_has_no_numbering():
    combined = combine_sub_answers(
        [
            SubQuestionResult(
                sub_question_id=1,
                question="Who crewed Apollo 11?",
                initial_answer="Neil Armstrong.",
                final_answer="Neil Armstrong.",
                stop_reason=SubQuestionStopReason.RESOLVED,
                iteration_count=1,
            )
        ]
    )
    assert combined == "Neil Armstrong"
    assert "1." not in combined
    assert "[" not in combined


def test_resolved_sentence_answer_prefers_terminal_object():
    combined = combine_sub_answers(
        [
            SubQuestionResult(
                sub_question_id=1,
                question="Who crewed Apollo 11?",
                initial_answer="Apollo 11 was crewed by Neil Armstrong",
                final_answer="Apollo 11 was crewed by Neil Armstrong",
                stop_reason=SubQuestionStopReason.RESOLVED,
                iteration_count=1,
                evidence_path={
                    "start_entity": "Apollo 11",
                    "terminal_claim": {
                        "subject": "Apollo 11",
                        "relation": "was_crewed_by",
                        "object": "Neil Armstrong",
                    },
                    "evidence_path": [
                        {
                            "subject": "Apollo 11",
                            "relation": "was_crewed_by",
                            "object": "Neil Armstrong",
                        }
                    ],
                    "path_length": 1,
                    "complete": True,
                },
                evidence_path_complete=True,
                evidence_path_length=1,
            )
        ]
    )
    assert combined == "Neil Armstrong"
