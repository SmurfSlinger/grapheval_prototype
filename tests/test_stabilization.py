"""Stabilization tests for projection, dates, quantities, and abstention."""

from __future__ import annotations

import pytest

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import SubQuestion, SubQuestionInitialAnswer, SubQuestionStopReason
from src.pipeline.abstention_detection import is_abstention_answer, is_factual_negation_answer
from src.pipeline.date_range_normalize import date_intervals_equivalent, parse_date_interval
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.kgc_iteration import KgcIterationEngine, determine_stop_reason
from src.pipeline.labeled_field_projection import (
    project_labeled_fields,
    validate_projection_faithfulness,
)
from src.pipeline.collection_amount_extract import extract_collection_amount_phrase
from src.pipeline.question_target import extract_answer_value
from src.pipeline.sub_answer_projector import SubAnswerProjector
from src.pipeline.target_frame_normalizer import objects_compatible_for_intent
from src.pipeline.working_kgc import WorkingKgcState


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


APOLLO_SUB_QUESTIONS = [
    SubQuestion(id=1, question="When was the Apollo 11 mission?"),
    SubQuestion(id=2, question="Who were the astronauts on the mission?"),
    SubQuestion(id=3, question="Where was it launched from?"),
    SubQuestion(id=4, question="Who was the president at the time?"),
    SubQuestion(id=5, question="How much lunar material was collected?"),
]


def test_preset_labeled_answer_projects_deterministically():
    example = _example("apollo_complex")
    answers = project_labeled_fields(example.initial_answer or "", APOLLO_SUB_QUESTIONS)
    assert answers is not None
    assert len(answers) == 5
    by_id = {item.sub_question_id: item.answer for item in answers}
    assert "1985" in by_id[1]
    assert "jessica" in by_id[2].lower()
    assert "airport" in by_id[3].lower()
    assert "trump" in by_id[4].lower()
    assert "7 ounce" in by_id[5].lower()


def test_all_five_wrong_apollo_values_preserved():
    example = _example("apollo_complex")
    projector = SubAnswerProjector(MockProvider())
    answers, trace = projector.project(
        example.question,
        APOLLO_SUB_QUESTIONS,
        example.initial_answer or "",
    )
    assert trace.method == "deterministic_labeled_fields"
    by_id = {item.sub_question_id: item.answer for item in answers}
    assert by_id[1] == "july 16-august 5, 1985"
    assert by_id[2] == "Neil Armstrong, Jessica Davis, Buzz Lightyear"
    assert by_id[3] == "John F Kennedy Airport"
    assert by_id[4] == "Donald Trump"
    assert by_id[5] == "7 ounces"


def test_projector_faithfulness_rejects_trusted_context_substitution():
    source = "Mission dates: july 16-august 5, 1985. Astronauts: Neil Armstrong."
    bad = [
        SubQuestionInitialAnswer(sub_question_id=1, answer="July 16-24, 1969"),
        SubQuestionInitialAnswer(sub_question_id=2, answer="Neil Armstrong"),
    ]
    assert not validate_projection_faithfulness(source, bad)


@pytest.mark.parametrize(
    ("left", "right", "equivalent"),
    [
        ("July 16-24, 1969", "July 16 to July 24, 1969", True),
        ("July 16-24, 1969", "July 16 to 24, 1969", True),
        ("July 16-24, 1969", "July 16 and 24, 1969", True),
        ("July 16-24, 1969", "between July 16 and 24, 1969", True),
        ("july 16-august 5, 1985", "July 16-24, 1969", False),
        ("July 16-24, 1969", "July 16, 1969", False),
    ],
)
def test_date_range_equivalence(left: str, right: str, equivalent: bool):
    assert date_intervals_equivalent(left, right) is equivalent


def test_wrong_year_date_interval_differs():
    left = parse_date_interval("July 16-24, 1969")
    right = parse_date_interval("July 16-24, 1985")
    assert left is not None and right is not None
    assert left != right


def test_collection_amount_extraction_stops_before_trailing_clause():
    sentence = (
        "21.5 kg (47.5 lb) of lunar material was collected during the Apollo 11 mission."
    )
    phrase = extract_collection_amount_phrase(sentence)
    assert phrase == "21.5 kg (47.5 lb) of lunar material"
    value = extract_answer_value(sentence, "collection_amount")
    assert value == phrase
    assert "apollo" not in value.lower()


def test_collection_amount_wrong_answer_preserved():
    assert extract_answer_value("7 ounces", "collection_amount") == "7 ounces"


def test_collection_amount_objects_compatible():
    left = "21.5 kg (47.5 lb) of lunar material"
    right = (
        "21.5 kg (47.5 lb) of lunar material was collected during the Apollo 11 mission."
    )
    assert objects_compatible_for_intent(left, right, "collection_amount")


def test_q4_abstention_wording_detected():
    answer = (
        "The provided KGc facts do not contain information stating who the president "
        "was at the time of the Apollo 11 mission."
    )
    assert is_abstention_answer(answer)


@pytest.mark.parametrize(
    "answer",
    [
        "There is no information in the provided knowledge graph.",
        "Not enough information to determine the president.",
        "Cannot be determined from the provided facts.",
        "The context does not state who was president.",
    ],
)
def test_common_abstention_wording_detected(answer: str):
    assert is_abstention_answer(answer)


def test_factual_negation_not_misclassified_as_abstention():
    assert is_factual_negation_answer("Apollo 11 did not launch from Florida")
    assert not is_abstention_answer("Apollo 11 did not launch from Florida")


def test_context_does_not_say_is_abstention():
    assert is_abstention_answer("The context does not say where Apollo 11 launched")


def test_repeated_abstention_stops_immediately():
    answer = "The provided KGc facts do not contain information."
    stop, reason = determine_stop_reason(
        iteration=1,
        max_iterations=3,
        current_answer=answer,
        previous_answer=answer,
        previous_signature="",
        current_signature="",
        supported_count=0,
        contradicted_count=0,
        no_evidence_count=0,
        claim_count=0,
        answer_is_abstention=True,
    )
    assert stop == SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE
    assert reason == "repeated_abstention"


def test_abstention_after_revision_stops_without_claims():
    answer = "The provided KGc facts do not contain information."
    stop, reason = determine_stop_reason(
        iteration=1,
        max_iterations=3,
        current_answer=answer,
        previous_answer="Donald Trump",
        previous_signature="sig",
        current_signature="",
        supported_count=0,
        contradicted_count=0,
        no_evidence_count=0,
        claim_count=0,
        answer_is_abstention=True,
    )
    assert stop == SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE
    assert reason == "abstention_after_revision"


def test_abstention_does_not_create_claim_triple():
    example = _example("apollo_complex")
    state = WorkingKgcState([])
    answer = (
        "The provided KGc facts do not contain information stating who the president "
        "was at the time of the Apollo 11 mission."
    )
    _, history, _, _ = KgcIterationEngine(MockProvider()).run_sub_question(
        question="Who was the president at the time?",
        trusted_context=example.context,
        working_state=state,
        sub_question_id=4,
        initial_answer=answer,
        max_iterations=2,
    )
    assert all(len(h.extracted_claims) == 0 for h in history)
    assert history[0].answer_is_abstention


def test_decomposed_run_preserves_projection_trace():
    result = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
        answer_0_mode="preset",
    ).run_example(_example("apollo_complex"))
    assert result.trace.projection_method == "deterministic_labeled_fields"
    assert result.trace.projection_faithfulness_passed is True
    assert result.trace.projection_source == _example("apollo_complex").initial_answer


def test_focused_extraction_trace_fields_present():
    result = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=2,
    ).run_example(_example("apollo_complex"))
    q3 = next(r for r in result.sub_question_results if "launch" in r.question.lower())
    assert q3.focused_extraction_raw is not None
    assert q3.focused_extraction_filtered is not None
    assert q3.focused_extraction_merged is not None
