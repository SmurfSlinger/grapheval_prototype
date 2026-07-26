"""Regression tests for structured-triple validation and the object bug."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.pipeline.structured_output import (
    StructuredOutputError,
    parse_claims_response,
    parse_context_facts_csv,
    parse_context_facts_response,
    get_last_parse_anomalies,
)
from src.pipeline.structured_triple_validation import coerce_raw_triple_item


FIXTURES = Path(__file__).parent / "fixtures"


def test_correct_array_subject_relation_object_parsing():
    validated, anomaly = coerce_raw_triple_item(
        ["System Alpha", "uses", "Service A"],
        kind="fact",
        source_stage="test",
    )
    assert anomaly is None
    assert validated is not None
    assert validated.subject == "System Alpha"
    assert validated.relation == "uses"
    assert validated.object == "Service A"
    assert "positional_array" in validated.normalization_applied


def test_correct_dictionary_parsing():
    validated, anomaly = coerce_raw_triple_item(
        {
            "subject": "Service A",
            "relation": "depends_on",
            "object": "Database B",
            "evidence": "Service A depends on Database B.",
        },
        kind="fact",
    )
    assert anomaly is None
    assert validated is not None
    assert validated.object == "Database B"
    assert validated.evidence == "Service A depends on Database B."


def test_missing_third_element_rejected():
    validated, anomaly = coerce_raw_triple_item(
        {"subject": "Host C", "relation": "located_in"},
        kind="fact",
    )
    assert validated is None
    assert anomaly is not None
    assert anomaly.reason == "missing_third_element"


def test_null_object_rejected_not_coerced_to_none_string():
    """Root-cause regression: str(None) previously produced object='None'."""
    validated, anomaly = coerce_raw_triple_item(
        {"subject": "Host C", "relation": "located_in", "object": None},
        kind="fact",
    )
    assert validated is None
    assert anomaly is not None
    assert anomaly.reason == "null_object"

    with pytest.raises(StructuredOutputError):
        parse_context_facts_response(
            json.dumps(
                {
                    "triples": [
                        {
                            "subject": "Host C",
                            "relation": "located_in",
                            "object": None,
                        }
                    ]
                }
            )
        )
    anomalies = get_last_parse_anomalies()
    assert any(item.reason == "null_object" for item in anomalies)


def test_nested_object_value_rejected():
    validated, anomaly = coerce_raw_triple_item(
        {
            "subject": "Host C",
            "relation": "located_in",
            "object": {"name": "Rack R7"},
        },
        kind="fact",
    )
    assert validated is None
    assert anomaly is not None
    assert anomaly.reason == "object_unsupported_nested_value"


def test_swapped_or_malformed_positional_values():
    validated, anomaly = coerce_raw_triple_item(
        ["System Alpha", "uses"],
        kind="fact",
    )
    assert validated is None
    assert anomaly is not None
    assert anomaly.reason == "malformed_array_too_short"

    validated2, anomaly2 = coerce_raw_triple_item(
        ["A", "uses", "B", "evidence", "extra"],
        kind="fact",
    )
    assert validated2 is None
    assert anomaly2 is not None
    assert anomaly2.reason == "malformed_array_extra_positional_fields"


def test_real_captured_null_object_failure_fixture():
    fixture = FIXTURES / "structured_triple_null_object_failure.json"
    raw = fixture.read_text(encoding="utf-8")
    with pytest.raises(StructuredOutputError):
        parse_context_facts_response(raw)
    anomalies = get_last_parse_anomalies()
    assert any(item.reason == "null_object" for item in anomalies)


def test_valid_existing_apollo_extraction():
    text = """subject,relation,object,evidence
Apollo 11,crewed_by,Neil Armstrong,crewed by Neil Armstrong
Neil Armstrong,born_in_town,Wapakoneta,born in Wapakoneta
Wapakoneta,located_in_state,Ohio,Wapakoneta is in Ohio
"""
    facts = parse_context_facts_csv(text)
    assert len(facts) == 3
    assert facts[2].subject == "Wapakoneta"
    assert facts[2].relation == "located_in_state"
    assert facts[2].object == "Ohio"


def test_valid_patient_d314_extraction():
    text = json.dumps(
        {
            "triples": [
                {
                    "subject": "Patient D-314",
                    "relation": "has_diagnosis",
                    "object": "Type 2 diabetes",
                    "evidence": "Patient D-314 has Type 2 diabetes.",
                },
                {
                    "subject": "Patient D-314",
                    "relation": "has_a1c",
                    "object": "7.2%",
                    "evidence": "Most recent A1c is 7.2%.",
                },
            ]
        }
    )
    facts = parse_context_facts_response(text)
    assert len(facts) == 2
    assert facts[0].object == "Type 2 diabetes"
    assert facts[1].object == "7.2%"


def test_mixed_valid_and_null_keeps_valid_triples():
    text = json.dumps(
        {
            "triples": [
                {
                    "subject": "System Alpha",
                    "relation": "uses",
                    "object": "Service A",
                },
                {
                    "subject": "Host C",
                    "relation": "located_in",
                    "object": None,
                },
                {
                    "subject": "Host C",
                    "relation": "located_in",
                    "object": "Rack R7",
                },
            ]
        }
    )
    facts = parse_context_facts_response(text)
    assert [(f.subject, f.relation, f.object) for f in facts] == [
        ("System Alpha", "uses", "Service A"),
        ("Host C", "located_in", "Rack R7"),
    ]
    anomalies = get_last_parse_anomalies()
    assert len(anomalies) == 1
    assert anomalies[0].reason == "null_object"


def test_title_case_csv_headers_map_fields_correctly():
    text = """Subject,Relation,Object,Evidence
Host C,located_in,Rack R7,Host C is located in Rack R7.
"""
    facts = parse_context_facts_csv(text)
    assert len(facts) == 1
    assert facts[0].object == "Rack R7"


def test_predicate_alias_normalization_recorded():
    validated, anomaly = coerce_raw_triple_item(
        {
            "subject": "Database B",
            "predicate": "runs_on",
            "object": "Host C",
        },
        kind="fact",
    )
    assert anomaly is None
    assert validated is not None
    assert validated.relation == "runs_on"
    assert "alias_predicate_to_relation" in validated.normalization_applied


def test_object_equal_to_relation_is_anomaly():
    validated, anomaly = coerce_raw_triple_item(
        {"subject": "A", "relation": "uses", "object": "uses"},
        kind="fact",
    )
    assert validated is None
    assert anomaly is not None
    assert anomaly.reason == "object_copied_from_relation"


def test_claims_parser_rejects_nested_object():
    with pytest.raises(StructuredOutputError):
        parse_claims_response(
            json.dumps(
                {
                    "triples": [
                        {
                            "subject": "Host C",
                            "relation": "located_in",
                            "object": ["Rack R7"],
                        }
                    ]
                }
            )
        )
