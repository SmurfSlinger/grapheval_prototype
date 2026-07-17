"""Structural validation for the first multi-hop measurement set."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace

from src.models import SubQuestionStopReason
from scripts.run_multihop_benchmark import (
    base_result_row,
    contains_expected_answer,
    failure_category,
    load_prior_results,
    normalize_answer,
    normalized_match,
    partition_resume_selection,
    select_questions,
    should_skip_prior_row,
    sub_questions_resolved,
    summarize,
    validate_test_set,
)


PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "test_sets"
    / "apollo_multihop_50.json"
)


def test_apollo_multihop_set_has_expected_coverage_and_paths():
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    questions = payload["questions"]
    facts = {tuple(fact) for fact in payload["expected_graph_facts"]}
    validation = validate_test_set(payload)

    assert validation["valid"], validation["errors"]
    assert payload["root_entity"] == "Apollo 11"
    assert len(questions) == 50
    assert len(facts) == len(payload["expected_graph_facts"]) == 48
    assert Counter(item["hop_count"] for item in questions) == {
        hop: 5 for hop in range(1, 11)
    }
    assert len({item["id"] for item in questions}) == 50

    for item in questions:
        assert len(item["expected_path"]) == item["hop_count"]
        assert item["expected_path"][0][0] == payload["root_entity"]
        assert all(tuple(edge) in facts for edge in item["expected_path"])
        assert all(
            left[2] == right[0]
            for left, right in zip(
                item["expected_path"],
                item["expected_path"][1:],
                strict=False,
            )
        )
        assert item["expected_answer"] == item["expected_path"][-1][2]
        assert set(item["required_relations"]) == {
            edge[1] for edge in item["expected_path"]
        }
        path_entities = {
            entity
            for subject, _, obj in item["expected_path"]
            for entity in (subject, obj)
        }
        assert set(item["required_entities"]) == path_entities


def test_benchmark_normalized_match_accepts_answer_in_a_grounded_sentence():
    assert normalized_match(
        "Apollo 11 was crewed by Neil Armstrong.",
        "Neil Armstrong",
    )
    assert not normalized_match(
        "Apollo 11 was crewed by Buzz Aldrin.",
        "Neil Armstrong",
    )


def test_answer_match_and_pipeline_resolution_remain_separate_metrics():
    question = {
        "id": "separation_test",
        "hop_count": 1,
        "question": "Who crewed Apollo 11?",
        "expected_answer": "Neil Armstrong",
        "expected_path": [["Apollo 11", "crewed_by", "Neil Armstrong"]],
        "required_entities": ["Apollo 11", "Neil Armstrong"],
        "required_relations": ["crewed_by"],
        "requires_alias_resolution": False,
        "requires_avoiding_sibling_branches": False,
        "requires_composed_answer": False,
        "requires_carry_forward": False,
    }
    predicted = "Apollo 11 was crewed by Neil Armstrong."
    row = base_result_row(
        question,
        provider_name="ollama",
        model="test-model",
        num_ctx=32768,
    )
    row.update(
        {
            "predicted_answer": predicted,
            "normalized_predicted": normalize_answer(predicted),
            "contains_expected_answer": contains_expected_answer(
                predicted,
                question["expected_answer"],
            ),
            "answer_match": normalized_match(
                predicted,
                question["expected_answer"],
            ),
            "resolved_by_pipeline": False,
            "final_stop_reason": "unresolved_target_not_satisfied",
            "error": None,
        }
    )
    row["failure_category"] = failure_category(
        error=None,
        resolved_by_pipeline=row["resolved_by_pipeline"],
        contains_expected=row["contains_expected_answer"],
        final_stop_reason=row["final_stop_reason"],
    )

    summary = summarize([row])
    assert row["contains_expected_answer"] is True
    assert row["resolved_by_pipeline"] is False
    assert row["failure_category"] == (
        "answer_matched_textually_but_pipeline_unresolved"
    )
    assert summary["contains_expected_count"] == 1
    assert summary["pipeline_resolved_count"] == 0
    assert summary["unresolved_but_answer_contained_expected_count"] == 1


def test_benchmark_question_selection_supports_ids_start_and_limit():
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    selected = select_questions(
        payload["questions"],
        ids="apollo_hop_001,apollo_hop_011,apollo_hop_021",
        start_at="apollo_hop_011",
        limit=1,
    )

    assert [item["id"] for item in selected] == ["apollo_hop_011"]


def test_pipeline_resolved_uses_stop_reason_enum_not_string_casing():
    resolved = SimpleNamespace(stop_reason=SubQuestionStopReason.RESOLVED)
    stalled = SimpleNamespace(stop_reason=SubQuestionStopReason.STALLED)

    assert sub_questions_resolved([resolved]) is True
    assert sub_questions_resolved([resolved, stalled]) is False


def test_resume_loads_prior_rows_and_skips_completed(tmp_path: Path):
    report_path = tmp_path / "partial.json"
    report_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "id": "apollo_hop_001",
                        "contains_expected_answer": True,
                        "resolved_by_pipeline": True,
                        "error": None,
                    },
                    {
                        "id": "apollo_hop_002",
                        "contains_expected_answer": False,
                        "resolved_by_pipeline": False,
                        "error": "TimeoutError: exceeded",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    prior = load_prior_results(report_path)
    assert set(prior) == {"apollo_hop_001", "apollo_hop_002"}
    assert should_skip_prior_row(
        prior["apollo_hop_001"],
        resume=True,
        rerun_errors=True,
    )
    assert not should_skip_prior_row(
        prior["apollo_hop_002"],
        resume=True,
        rerun_errors=True,
    )
    assert should_skip_prior_row(
        prior["apollo_hop_002"],
        resume=True,
        rerun_errors=False,
    )
    assert not should_skip_prior_row(None, resume=True, rerun_errors=False)


def test_resume_with_start_at_keeps_earlier_ids_in_report_selection():
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    report_selection, runnable_ids = partition_resume_selection(
        payload["questions"],
        ids=None,
        start_at="apollo_hop_011",
        limit=None,
        resume=True,
    )
    assert report_selection[0]["id"] == "apollo_hop_001"
    assert "apollo_hop_001" not in runnable_ids
    assert "apollo_hop_011" in runnable_ids
    assert len(report_selection) == 50
    assert len(runnable_ids) == 40
