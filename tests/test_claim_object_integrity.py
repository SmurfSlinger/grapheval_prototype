"""Regression tests for claim object integrity across grounding and alignment."""

from __future__ import annotations

from src.models import KgcFact, Triple
from src.pipeline.claim_grounding import ground_claim_objects_in_answer
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema


def test_atomic_object_preserved_when_present_in_answer():
    claims = [Triple("Host C", "located_in", "Rack R7", "Host C is in Rack R7.")]
    grounded, traces = ground_claim_objects_in_answer(claims, "Host C is in Rack R7.")
    assert grounded[0].object == "Rack R7"
    assert traces == []


def test_atomic_object_not_broadened_to_source_sentence():
    answer = "The host that runs Database B is located in Rack R7 according to the chart."
    claims = [
        Triple(
            "Host C",
            "located_in",
            "Rack R7",
            source_sentence=answer,
        )
    ]
    grounded, traces = ground_claim_objects_in_answer(claims, answer)
    assert grounded[0].object == "Rack R7"
    assert all(t.after != answer for t in traces)


def test_sentence_answer_does_not_replace_atomic_object():
    answer = (
        "After reviewing the dependency chain, I conclude the machine sits in Rack R7 "
        "near the cooling aisle."
    )
    claims = [Triple("Host C", "located_in", "Rack R7")]
    grounded, _ = ground_claim_objects_in_answer(claims, answer)
    assert grounded[0].object == "Rack R7"


def test_incorrect_answer_object_preserved_against_correct_kgc():
    kgc = [KgcFact("Host C", "located_in", "Rack R7", evidence="trusted")]
    claim = Triple("Host C", "located_in", "Rack R9", "The host is in Rack R9.")
    grounded, _ = ground_claim_objects_in_answer(
        [claim], "The host is in Rack R9."
    )
    aligned, traces = align_claims_to_kgc_schema(grounded, kgc)
    assert grounded[0].object == "Rack R9"
    assert aligned[0].object == "Rack R9"
    assert all(t.field != "object" for t in traces)


def test_alignment_never_copies_kgc_object_into_claim():
    kgc = [
        KgcFact("Apollo 11", "launched_from", "Kennedy Space Center", evidence="ctx"),
    ]
    claim = Triple("Apollo 11", "was_launched_from", "Florida")
    aligned, traces = align_claims_to_kgc_schema([claim], kgc)
    assert aligned[0].object == "Florida"
    assert all(t.field != "object" for t in traces)
    assert any(t.field in {"subject", "relation"} for t in traces) or aligned[
        0
    ].relation != claim.relation or aligned[0].subject != claim.subject


def test_alignment_traces_include_before_after_reason_stage():
    kgc = [KgcFact("Host C", "located_in", "Rack R7")]
    claim = Triple("Location label", "has_value", "Rack R7")
    aligned, traces = align_claims_to_kgc_schema([claim], kgc)
    assert aligned[0].subject == "Host C"
    assert aligned[0].object == "Rack R7"
    assert traces
    for trace in traces:
        payload = trace.to_dict()
        assert payload["before"] != payload["after"]
        assert payload["reason"]
        assert payload["source_stage"] == "schema_alignment"
        assert {"field", "before", "after", "reason", "source_stage"} <= set(payload)


def test_grounding_keeps_answer_object_not_kgc_leak():
    claims = [
        Triple(
            "Host C",
            "located_in",
            "Rack R9",
            source_sentence="Rack R9",
        )
    ]
    grounded, traces = ground_claim_objects_in_answer(claims, "Rack R9")
    assert grounded[0].object == "Rack R9"
    assert all(t.after != "Rack R7" for t in traces)


def test_grounding_traces_include_before_after_reason_stage():
    claims = [
        Triple(
            "Host C",
            "located_in",
            "somewhere unknown",
            source_sentence="Rack R7",
        )
    ]
    grounded, traces = ground_claim_objects_in_answer(
        claims, "Host C is located in Rack R7."
    )
    assert grounded[0].object == "Rack R7"
    assert traces
    for trace in traces:
        payload = trace.to_dict()
        assert payload["before"]
        assert payload["after"]
        assert payload["reason"]
        assert payload["source_stage"] == "claim_grounding"
