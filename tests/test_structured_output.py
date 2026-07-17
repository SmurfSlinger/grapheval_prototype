"""Tests for structured CSV/JSON output parsing."""

from __future__ import annotations

import pytest

from src.models import SubQuestion
from src.pipeline.structured_output import (
    StructuredOutputError,
    complete_with_retry,
    parse_claims_csv,
    parse_claims_response,
    parse_context_facts_csv,
    parse_context_facts_response,
    parse_question_split_response,
)


def test_parse_context_facts_csv_valid():
    text = """subject,relation,object,evidence
Apollo 11,launched_by,Saturn V,launched by a Saturn V rocket
"""
    facts = parse_context_facts_csv(text)
    assert len(facts) == 1
    assert facts[0].subject == "Apollo 11"
    assert facts[0].relation == "launched_by"


def test_parse_claims_csv_valid():
    text = """subject,relation,object,source_sentence
Apollo 11,launched_from,Cape Canaveral,from Cape Canaveral
"""
    claims = parse_claims_csv(text)
    assert len(claims) == 1
    assert claims[0].object == "Cape Canaveral"


def test_kgc_extraction_error_to_dict_includes_message_and_attempts():
    from src.pipeline.structured_output import (
        ExtractionAttempt,
        KgcExtractionError,
        StructuredExtractionTrace,
    )

    trace = StructuredExtractionTrace(
        stage="context_triple_extraction",
        format_used="json",
        retry_count=1,
        attempts=[
            ExtractionAttempt(
                attempt=1,
                format="json",
                raw_preview='{"triples": [',
                error="Invalid JSON response.",
            )
        ],
    )
    exc = KgcExtractionError("Context triple extraction failed", trace=trace)
    payload = exc.to_dict()
    assert payload["message"] == str(exc)
    assert payload["stage"] == "context_triple_extraction"
    assert payload["attempts"][0]["error"] == "Invalid JSON response."


def test_parse_context_facts_json_legacy():
    text = '{"triples": [{"subject": "A", "relation": "r", "object": "o"}]}'
    facts = parse_context_facts_response(text)
    assert len(facts) == 1


def test_parse_claims_json_legacy():
    text = '{"triples": [{"subject": "A", "relation": "r", "object": "o"}]}'
    claims = parse_claims_response(text)
    assert len(claims) == 1


def test_parse_context_facts_json_repairs_truncated_closing_brace():
    text = """{
"triples": [
{
"subject": "Apollo 11",
"relation": "launched_from",
"object": "Kennedy Space Center in Florida",
"evidence": "Launched from Kennedy Space Center in Florida"
}
]
"""
    facts = parse_context_facts_response(text)
    assert len(facts) == 1
    assert facts[0].object == "Kennedy Space Center in Florida"


def test_malformed_csv_rejected():
    with pytest.raises(StructuredOutputError):
        parse_claims_csv("subject,relation,object,source_sentence\nA,r,,")


def test_csv_skips_blank_trailing_rows():
    text = """subject,relation,object,source_sentence
Apollo 11,launched_from,Cape Canaveral,from Cape Canaveral

"""
    claims = parse_claims_csv(text)
    assert len(claims) == 1


def test_question_split_valid():
    text = """{"questions": [
        {"id": 1, "question": "What rocket launched Apollo 11?"},
        {"id": 2, "question": "Where did Apollo 11 launch from?"}
    ]}"""
    splits = parse_question_split_response(text)
    assert splits == [
        SubQuestion(id=1, question="What rocket launched Apollo 11?"),
        SubQuestion(id=2, question="Where did Apollo 11 launch from?"),
    ]


def test_question_split_rejects_bad_ids():
    text = '{"questions": [{"id": 2, "question": "Late start?"}]}'
    with pytest.raises(StructuredOutputError):
        parse_question_split_response(text)


def test_complete_with_retry_recovers():
    calls: list[str] = []

    def complete(prompt: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return "not csv"
        return "subject,relation,object,evidence\nA,b,c,d"

    facts, retries = complete_with_retry(complete, "prompt", parse_context_facts_response)
    assert retries == 1
    assert len(facts) == 1
