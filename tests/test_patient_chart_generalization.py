"""Regression tests for patient-chart generalization of decomposed KGc."""

from __future__ import annotations

from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.models import KgcClaimLabel, KgcFact, SubQuestion, SubQuestionStopReason, Triple
from src.pipeline.composite_claim_slots import build_composite_claims
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_matching import (
    ACTIVE_MED_RELATIONS,
    DISCONTINUED_MED_RELATIONS,
    DISCUSSED_NOT_STARTED_RELATIONS,
    INTENT_CANONICAL_RELATIONS,
)
from src.pipeline.labeled_field_projection import (
    parse_labeled_fields,
    project_labeled_fields,
    validate_projection_faithfulness,
)
from src.pipeline.question_target import (
    condition_claims_to_question,
    derive_question_target,
    evaluate_target_satisfaction,
)
from src.pipeline.target_frame_normalizer import relations_share_target_family as share_family


def _example(example_id: str):
    return next(ex for ex in load_examples() if ex.id == example_id)


def _patient_kgc() -> list[KgcFact]:
    return [
        KgcFact("Patient Case D-314", "diagnosed_with", "type 2 diabetes mellitus"),
        KgcFact("Patient Case D-314", "has_a1c", "9.1%"),
        KgcFact("Patient Case D-314", "has_ckd_stage", "stage 3b"),
        KgcFact("Patient Case D-314", "has_egfr", "38 mL/min/1.73 m²"),
        KgcFact("Patient Case D-314", "discontinued_medication", "metformin"),
        KgcFact(
            "Patient Case D-314",
            "discontinued_because",
            "severe gastrointestinal intolerance",
        ),
        KgcFact("Patient Case D-314", "active_medication", "empagliflozin"),
        KgcFact("Patient Case D-314", "daily_dose", "10 mg daily"),
        KgcFact("Patient Case D-314", "discussed_not_started", "semaglutide"),
        KgcFact("Patient Case D-314", "allergic_to", "penicillin"),
        KgcFact("Patient Case D-314", "causes_reaction", "hives"),
    ]


def test_patient_example_exists_with_expected_fields():
    ex = _example("patient_d_314_complex")
    fields = parse_labeled_fields(ex.initial_answer)
    assert [label for label, _ in fields] == [
        "Diagnosis",
        "A1C",
        "Kidney disease",
        "Medication stopped",
        "Current tolerated medication",
        "Discussed but not started",
        "Antibiotic allergy",
    ]
    assert fields[0][1] == "type 2 diabetes mellitus"
    assert fields[1][1] == "6.2%"
    assert "78" in fields[2][1]
    assert "hypoglycemia" in fields[3][1]
    assert "25 mg" in fields[4][1]
    assert fields[5][1] == "insulin glargine"
    assert "anaphylaxis" in fields[6][1]


def test_projection_preserves_flawed_values():
    ex = _example("patient_d_314_complex")
    splits = MockProvider.QUESTION_SPLITS[
        "what diabetes diagnosis is documented for patient case d-314"
    ]
    sub_questions = [SubQuestion(id=item["id"], question=item["question"]) for item in splits]
    projected = project_labeled_fields(ex.initial_answer, sub_questions)
    assert projected is not None
    assert validate_projection_faithfulness(ex.initial_answer, projected)
    values = [item.answer for item in projected]
    assert values[0] == "type 2 diabetes mellitus"
    assert values[1] == "6.2%"
    assert "78" in values[2]
    assert "hypoglycemia" in values[3]
    assert "25 mg" in values[4]
    assert values[5] == "insulin glargine"
    assert "anaphylaxis" in values[6]


def test_medical_intents_have_canonical_relations():
    kgc = _patient_kgc()
    cases = [
        ("What diabetes diagnosis is documented for Patient Case D-314?", "diagnosis"),
        ("What is the latest A1C?", "lab_measurement"),
        (
            "What CKD stage is documented and what is the current eGFR?",
            "kidney_status",
        ),
        (
            "Which diabetes medication was discontinued and why?",
            "discontinued_medication_with_reason",
        ),
        (
            "Which diabetes medication is currently active and tolerated, and at what dose?",
            "active_medication_with_dose",
        ),
        (
            "Which medication was discussed but has not been started?",
            "discussed_not_started",
        ),
        (
            "What antibiotic allergy and reaction are recorded?",
            "allergy_with_reaction",
        ),
    ]
    for question, intent in cases:
        target = derive_question_target(question, kgc)
        assert target.intent == intent, question
        assert target.canonical_relation is not None, intent
        assert target.canonical_relation == INTENT_CANONICAL_RELATIONS[intent]


def test_kidney_partial_correctness_mixed_labels():
    kgc = _patient_kgc()
    question = "What CKD stage is documented and what is the current eGFR?"
    target = derive_question_target(question, kgc)
    answer = "CKD stage 3b with eGFR 78 mL/min/1.73 m²"
    claims = condition_claims_to_question([], question, answer, target, kgc)
    assert len(claims) == 2
    relations = {c.relation for c in claims}
    assert "has_ckd_stage" in relations
    assert "has_egfr" in relations

    evaluated = GraphComparator().compare_claims(
        claims, kgc, question_target=target, question=question
    )
    labels = {ev.triple.relation: ev.label for ev in evaluated}
    assert labels["has_ckd_stage"] == KgcClaimLabel.SUPPORTED
    assert labels["has_egfr"] == KgcClaimLabel.CONTRADICTED

    satisfaction = evaluate_target_satisfaction(evaluated, target)
    assert satisfaction.satisfied is False
    assert satisfaction.on_target_supported_count == 1


def test_kidney_corrected_egfr_supported():
    kgc = _patient_kgc()
    question = "What CKD stage is documented and what is the current eGFR?"
    target = derive_question_target(question, kgc)
    answer = "CKD stage 3b with eGFR 38 mL/min/1.73 m²"
    claims = condition_claims_to_question([], question, answer, target, kgc)
    evaluated = GraphComparator().compare_claims(
        claims, kgc, question_target=target, question=question
    )
    assert all(ev.label == KgcClaimLabel.SUPPORTED for ev in evaluated)
    assert evaluate_target_satisfaction(evaluated, target).satisfied is True


def test_discontinued_med_preserves_identity_contradicts_reason():
    kgc = _patient_kgc()
    question = "Which diabetes medication was discontinued and why?"
    target = derive_question_target(question, kgc)
    answer = "metformin because of recurrent hypoglycemia"
    claims = condition_claims_to_question([], question, answer, target, kgc)
    evaluated = GraphComparator().compare_claims(
        claims, kgc, question_target=target, question=question
    )
    by_rel = {ev.triple.relation: ev for ev in evaluated}
    assert by_rel["discontinued_medication"].label == KgcClaimLabel.SUPPORTED
    assert by_rel["discontinued_because"].label == KgcClaimLabel.CONTRADICTED


def test_active_med_preserves_identity_contradicts_dose():
    kgc = _patient_kgc()
    question = (
        "Which diabetes medication is currently active and tolerated, and at what dose?"
    )
    target = derive_question_target(question, kgc)
    answer = "empagliflozin 25 mg daily"
    claims = condition_claims_to_question([], question, answer, target, kgc)
    evaluated = GraphComparator().compare_claims(
        claims, kgc, question_target=target, question=question
    )
    by_rel = {ev.triple.relation: ev for ev in evaluated}
    assert by_rel["active_medication"].label == KgcClaimLabel.SUPPORTED
    assert by_rel["daily_dose"].label == KgcClaimLabel.CONTRADICTED


def test_allergy_preserves_identity_contradicts_reaction():
    kgc = _patient_kgc()
    question = "What antibiotic allergy and reaction are recorded?"
    target = derive_question_target(question, kgc)
    answer = "penicillin causing anaphylaxis"
    claims = condition_claims_to_question([], question, answer, target, kgc)
    evaluated = GraphComparator().compare_claims(
        claims, kgc, question_target=target, question=question
    )
    by_rel = {ev.triple.relation: ev for ev in evaluated}
    assert by_rel["allergic_to"].label == KgcClaimLabel.SUPPORTED
    assert by_rel["causes_reaction"].label == KgcClaimLabel.CONTRADICTED


def test_medication_status_families_do_not_collapse():
    assert not share_family(
        "discontinued_medication",
        "active_medication",
        "medication_discontinued",
    )
    assert not share_family(
        "discussed_not_started",
        "active_medication",
        "discussed_not_started",
    )
    assert DISCONTINUED_MED_RELATIONS.isdisjoint(ACTIVE_MED_RELATIONS)
    assert DISCUSSED_NOT_STARTED_RELATIONS.isdisjoint(ACTIVE_MED_RELATIONS)
    assert DISCUSSED_NOT_STARTED_RELATIONS.isdisjoint(DISCONTINUED_MED_RELATIONS)


def test_composite_slot_matching_does_not_cross_stage_and_egfr():
    assert not share_family("has_ckd_stage", "has_egfr", "kidney_status")
    assert share_family("has_ckd_stage", "ckd_stage", "kidney_status")
    assert share_family("has_egfr", "egfr_value", "kidney_status")


def test_a1c_conflict_and_support():
    kgc = _patient_kgc()
    question = "What is the latest A1C?"
    target = derive_question_target(question, kgc)
    wrong = condition_claims_to_question(
        [], question, "6.2%", target, kgc
    )
    right = condition_claims_to_question(
        [], question, "9.1%", target, kgc
    )
    wrong_ev = GraphComparator().compare_claims(
        wrong, kgc, question_target=target, question=question
    )[0]
    right_ev = GraphComparator().compare_claims(
        right, kgc, question_target=target, question=question
    )[0]
    assert wrong_ev.label == KgcClaimLabel.CONTRADICTED
    assert right_ev.label == KgcClaimLabel.SUPPORTED


def test_discussed_not_started_not_active():
    kgc = _patient_kgc()
    question = "Which medication was discussed but has not been started?"
    target = derive_question_target(question, kgc)
    assert target.intent == "discussed_not_started"
    wrong = condition_claims_to_question(
        [], question, "insulin glargine", target, kgc
    )
    right = condition_claims_to_question(
        [], question, "semaglutide", target, kgc
    )
    wrong_ev = GraphComparator().compare_claims(
        wrong, kgc, question_target=target, question=question
    )[0]
    right_ev = GraphComparator().compare_claims(
        right, kgc, question_target=target, question=question
    )[0]
    assert wrong_ev.label == KgcClaimLabel.CONTRADICTED
    assert right_ev.label == KgcClaimLabel.SUPPORTED
    # Active medication fact must not support discussed_not_started claim.
    assert wrong[0].relation == "discussed_not_started"


def test_mock_patient_decomposed_resolves():
    ex = _example("patient_d_314_complex")
    result = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
        answer_0_mode="preset_external_projected",
    ).run_example(ex)
    assert result.trace.projection_method == "deterministic_labeled_fields"
    assert result.trace.projection_faithfulness_passed is True
    assert len(result.sub_question_results) == 7
    for sub in result.sub_question_results:
        assert sub.stop_reason == SubQuestionStopReason.RESOLVED, (
            sub.sub_question_id,
            sub.question,
            sub.stop_reason,
            sub.final_answer,
        )
        assert sub.question_target_satisfied is True


def test_apollo_complex_still_resolves_under_mock():
    ex = _example("apollo_complex")
    result = DecomposedBacktrackingRunner(
        MockProvider(),
        max_iterations_per_sub_question=3,
        answer_0_mode="preset",
    ).run_example(ex)
    resolved = sum(
        1
        for sub in result.sub_question_results
        if sub.stop_reason == SubQuestionStopReason.RESOLVED
    )
    assert resolved == 5


def test_bootstrap_facts_from_trusted_context():
    from src.pipeline.trusted_context_bootstrap import bootstrap_facts_from_context

    ex = _example("patient_d_314_complex")
    target = derive_question_target(
        "What is the latest A1C?",
        [],
        trusted_context=ex.context,
    )
    facts = bootstrap_facts_from_context(trusted_context=ex.context, target=target)
    assert len(facts) == 1
    assert facts[0].relation == "has_a1c"
    assert facts[0].object == "9.1%"
    assert "9.1" in (facts[0].evidence or "")


def test_composite_requires_all_slots_for_satisfaction():
    kgc = _patient_kgc()
    question = "What CKD stage is documented and what is the current eGFR?"
    target = derive_question_target(question, kgc)
    # Only eGFR present — must not count as target satisfied.
    claims = condition_claims_to_question(
        [], question, "eGFR 38 mL/min/1.73 m²", target, kgc
    )
    evaluated = GraphComparator().compare_claims(
        claims, kgc, question_target=target, question=question
    )
    assert evaluate_target_satisfaction(evaluated, target).satisfied is False


def test_filter_rejects_off_target_focused_facts():
    from src.pipeline.question_target import filter_minimal_focused_facts

    kgc = _patient_kgc()
    question = "What diabetes diagnosis is documented for Patient Case D-314?"
    target = derive_question_target(question, kgc)
    junk = [
        KgcFact(
            "chart",
            "has",
            "type 2 diabetes mellitus",
            evidence="Patient Case D-314 has type 2 diabetes mellitus",
        )
    ]
    assert filter_minimal_focused_facts(junk, target) == []


def test_active_med_extractor_handles_prose_sentence():
    from src.pipeline.composite_claim_slots import build_composite_claims

    claims = build_composite_claims(
        answer=(
            "Empagliflozin is currently active and tolerated at a dose of 10 mg daily."
        ),
        subject="Patient Case D-314",
        intent="active_medication_with_dose",
    )
    by_rel = {c.relation: c.object for c in claims}
    assert by_rel["active_medication"].lower() == "empagliflozin"
    assert "10" in by_rel["daily_dose"]
    assert by_rel["active_medication"].lower() != "of"


def test_build_composite_claims_no_hardcoded_patient_values():
    claims = build_composite_claims(
        answer="CKD stage 4 with eGFR 22 mL/min/1.73 m²",
        subject="Patient Case X-999",
        intent="kidney_status",
    )
    assert claims[0].object == "stage 4"
    assert "22" in claims[1].object
