"""Integration tests for KGc backtracking runner (MockProvider, no Neo4j)."""

from __future__ import annotations

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import KgcClaimLabel
from src.pipeline.kgc_matching import normalize_relation
from src.pipeline.backtracking_runner import (
    BacktrackingRunner,
    _detect_kgc_extraction_notice,
)


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def test_hyundai_mock_flow_evaluates_answer_0_and_produces_answer_1():
    """Answer(0) claims are evaluated against KGc; contradictions produce Answer(1)."""
    runner = BacktrackingRunner(MockProvider(), max_iterations=1)
    result = runner.run_example(_example("hyundai_sonata_001"))

    assert result.answer_0, "Answer(0) baseline should be present"
    assert "turbo" in result.answer_0 or "Korea" in result.answer_0

    relations = {fact.relation for fact in result.kgc_facts}
    assert "has_engine" in relations
    assert "assembled_in" in relations

    assert result.evaluated_answer == result.answer_0
    assert result.evaluated_answer_iteration == 0
    assert result.evaluated_claims, "Answer(0) claims should be evaluated against KGc"

    assert result.contradicted_count == 2, (
        "Flawed Answer(0) should have two contradicted claims"
    )
    assert result.supported_count == 0
    assert result.no_evidence_count == 0

    assert "2.4L engine" in result.answer_1
    assert "Alabama" in result.answer_1
    assert "turbo" not in result.answer_1.lower()
    assert "korea" not in result.answer_1.lower()


def test_drone_mock_flow_evaluates_answer_0_claims_against_kgc():
    """Drone: Answer(0) flaws are checked; supported does_not_carry is preserved."""
    runner = BacktrackingRunner(MockProvider(), max_iterations=1)
    result = runner.run_example(_example("drone_alpha_7_001"))

    relations = {fact.relation for fact in result.kgc_facts}
    assert "has_maximum_flight_time" in relations
    assert "approved_for" in relations
    assert "does_not_carry" in relations

    assert result.evaluated_answer == result.answer_0
    assert result.supported_count == 1, "does_not_carry weapons should be SUPPORTED"
    assert result.contradicted_count == 2, (
        "Flight time and recon approval should be CONTRADICTED"
    )
    assert result.no_evidence_count == 0

    assert "42 minutes" in result.answer_1
    assert "daylight" in result.answer_1.lower()
    assert "night" not in result.answer_1.lower()


def test_apollo_preset_shows_contradicted_claims_from_answer_0():
    """Apollo preset Answer(0) should contradict KGc on rocket, site, and engines."""
    runner = BacktrackingRunner(MockProvider(), max_iterations=1)
    result = runner.run_example(_example("saturn_v_apollo_11_001"))

    assert result.evaluated_answer == result.answer_0
    assert "Saturn IB" in result.answer_0
    assert "Cape Canaveral" in result.answer_0

    assert len(result.kgc_facts) == 5
    assert len(result.extracted_claims) == 4
    assert len(result.evaluated_claims) == 4

    extracted_relations = {claim.relation for claim in result.extracted_claims}
    assert "launched_from" in extracted_relations
    assert any(
        normalize_relation(rel) == "launched_by"
        for rel in extracted_relations
    )

    assert result.supported_count == 1
    assert result.contradicted_count == 3
    assert result.no_evidence_count == 0

    contradicted_objects = {
        ev.triple.object
        for ev in result.evaluated_claims
        if ev.label == KgcClaimLabel.CONTRADICTED
    }
    assert any("saturn ib" in obj.lower() for obj in contradicted_objects)
    assert "Cape Canaveral" in contradicted_objects
    assert any("j-2" in obj.lower() for obj in contradicted_objects)

    launch_kgc = {
        fact.object
        for fact in result.kgc_facts
        if fact.relation == "launched_from"
    }
    assert any("launch complex 39a" in obj.lower() for obj in launch_kgc)

    assert "Saturn V" in result.answer_1
    assert "Launch Complex 39A" in result.answer_1
    assert "Kennedy Space Center" in result.answer_1
    assert "F-1" in result.answer_1 or "f-1" in result.answer_1.lower()
    assert "Saturn IB" not in result.answer_1
    assert "Cape Canaveral" not in result.answer_1
    assert "J-2" not in result.answer_1

    assert result.revision_effect is not None
    assert result.revision_effect.preserved_supported_count == 1
    assert result.revision_effect.corrected_contradicted_count == 3
    assert result.revision_effect.removed_or_deferred_no_evidence_count == 0


def test_backtracking_result_includes_trace_and_claim_metadata():
    """API result should expose trace sources and per-claim evaluation metadata."""
    runner = BacktrackingRunner(MockProvider(), max_iterations=1)
    result = runner.run_example(_example("drone_alpha_7_001"))
    payload = result.to_dict()

    assert payload["trace"]["kgc_source"] == "extracted_from_trusted_context"
    assert payload["trace"]["claim_extraction_source"] == "extracted_from_answer_n"
    assert payload["trace"]["kgc_reference_answer_source"] == (
        "generated_from_question_plus_serialized_kgc"
    )
    assert payload["trace"]["answer_0_mode"] == "preset"
    assert payload["answer_0_mode"] == "preset"
    assert payload["evaluated_answer"] == payload["answer_0"]
    assert payload["evaluated_answer_iteration"] == 0
    assert len(payload["extracted_claims"]) == len(payload["aligned_claims"])
    assert payload["revision_effect"]["preserved_supported_count"] == 1
    assert payload["revision_effect"]["corrected_contradicted_count"] == 2

    supported = next(
        c for c in payload["evaluated_claims"] if c["label"] == "SUPPORTED"
    )
    assert supported["matched_kgc_fact"] is not None


def test_preset_mode_uses_initial_answer():
    runner = BacktrackingRunner(MockProvider(), max_iterations=1)
    example = _example("hyundai_sonata_001")
    result = runner.run_example(example, answer_0_mode="preset")

    assert result.answer_0 == example.initial_answer
    assert result.answer_0_mode == "preset"
    assert result.trace.answer_0_source == "example.initial_answer"
    assert result.answer_0_warning is None


def test_generated_mode_builds_answer_from_context():
    runner = BacktrackingRunner(MockProvider(), max_iterations=1)
    example = _example("hyundai_sonata_001")
    result = runner.run_example(example, answer_0_mode="generated")

    assert result.answer_0 != example.initial_answer
    assert result.answer_0_mode == "generated"
    assert result.trace.answer_0_source == "generated_from_raw_context"
    assert result.answer_0_warning is None


def test_preset_mode_falls_back_when_no_initial_answer():
    runner = BacktrackingRunner(MockProvider(), max_iterations=1)
    example = _example("hyundai_sonata_001")
    example.initial_answer = None
    result = runner.run_example(example, answer_0_mode="preset")

    assert result.answer_0_mode == "generated"
    assert result.trace.answer_0_source == "generated_from_raw_context"
    assert result.answer_0_warning is not None
    assert "no initial_answer" in result.answer_0_warning.lower()


def test_kgc_extraction_notice_detects_incomplete_graph_answer():
    notice = _detect_kgc_extraction_notice(
        "Flight time: not specified in KGc."
    )
    assert notice is not None
    assert "context-to-graph extraction" in notice.lower()
    assert "research" in notice.lower()
