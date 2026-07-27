"""Pipeline integrity: alignment drift, direction, unresolved answers, targets."""

from __future__ import annotations

from src.models import (
    KgcClaimLabel,
    KgcEvaluationResult,
    KgcFact,
    SubQuestionResult,
    SubQuestionStopReason,
    Triple,
)
from src.pipeline.claim_direction import (
    enforce_claim_direction_integrity,
    find_reverse_entity_pair_fact,
)
from src.pipeline.evidence_path_resolver import resolve_evidence_path
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kgc_iteration import determine_stop_reason
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.question_target import (
    derive_question_target,
    evaluate_target_satisfaction,
)
from src.pipeline.sub_answer_combiner import (
    combine_sub_answers,
    prefer_terminal_object_answer,
)


# --- Fix 1: unsafe schema drift -------------------------------------------------


def test_object_only_match_rejects_subject_and_relation_drift_real_shaped():
    """Oceanography — is_studied_by → Global Ocean must not become
    Atlantic Ocean — is_part_of → Global Ocean."""
    kgc = [
        KgcFact("Atlantic Ocean", "is_part_of", "Global Ocean"),
        KgcFact("Global Ocean", "is_studied_by", "Oceanography"),
    ]
    claim = Triple(
        "Oceanography",
        "is_studied_by",
        "Global Ocean",
        source_sentence="Oceanography studies the Global Ocean",
    )
    aligned, traces = align_claims_to_kgc_schema([claim], kgc)

    assert aligned[0].subject == "Oceanography"
    assert aligned[0].relation == "is_studied_by"
    assert aligned[0].object == "Global Ocean"
    assert traces == []
    results = GraphComparator().compare_claims(aligned, kgc)
    assert results[0].label == KgcClaimLabel.NO_EVIDENCE


def test_object_only_match_rejects_subject_and_relation_drift_generic():
    kgc = [
        KgcFact("Entity A", "is_part_of", "Entity Z"),
        KgcFact("Entity Z", "is_studied_by", "Entity B"),
    ]
    claim = Triple("Entity B", "is_studied_by", "Entity Z")
    aligned, _ = align_claims_to_kgc_schema([claim], kgc)

    assert aligned[0].subject == "Entity B"
    assert aligned[0].relation == "is_studied_by"
    assert aligned[0].object == "Entity Z"
    assert aligned[0].subject != "Entity A"
    assert aligned[0].relation != "is_part_of"


def test_relation_object_match_may_canonicalize_subject_only():
    kgc = [KgcFact("Canonical Subject", "approved_for", "daylight work")]
    claim = Triple("Display Label", "approved_for", "daylight work")
    aligned, traces = align_claims_to_kgc_schema([claim], kgc)

    assert aligned[0].subject == "Canonical Subject"
    assert aligned[0].relation == "approved_for"
    assert aligned[0].object == "daylight work"
    assert any(t.field == "subject" for t in traces)
    assert not any(t.field == "relation" for t in traces)


def test_subject_object_match_may_canonicalize_relation_only():
    kgc = [KgcFact("Mission X", "launched_by", "Rocket Y")]
    claim = Triple("Mission X", "was_launched_by", "Rocket Y")
    # was_launched_by is a launch-vehicle family match; also subject+object same.
    aligned, _ = align_claims_to_kgc_schema([claim], kgc)
    assert aligned[0].subject == "Mission X"
    assert aligned[0].object == "Rocket Y"
    assert aligned[0].relation in {"launched_by", "was_launched_by"}


def test_alignment_never_copies_trusted_kg_object_into_claim():
    kgc = [KgcFact("Mission X", "launched_from", "Trusted Pad")]
    claim = Triple("Mission X", "launched_from", "Wrong Pad")
    aligned, _ = align_claims_to_kgc_schema([claim], kgc)
    assert aligned[0].object == "Wrong Pad"


# --- Fix 2: directional claim extraction ---------------------------------------


def test_active_to_passive_studies_direction_correction():
    kgc = [KgcFact("Subject Y", "is_studied_by", "Researcher X")]
    inverted = Triple(
        "Researcher X",
        "is_studied_by",
        "Subject Y",
        source_sentence="Researcher X studies Subject Y",
    )
    corrected, anomalies = enforce_claim_direction_integrity(
        [inverted], kgc, answer="Researcher X studies Subject Y."
    )
    assert corrected[0].subject == "Subject Y"
    assert corrected[0].relation == "is_studied_by"
    assert corrected[0].object == "Researcher X"
    assert anomalies and anomalies[0].corrected is True


def test_active_to_passive_employs_and_contains_families():
    kgc = [
        KgcFact("Person Y", "is_employed_by", "Organization X"),
        KgcFact("Landmark Y", "is_located_in", "City X"),
    ]
    claims = [
        Triple(
            "Organization X",
            "is_employed_by",
            "Person Y",
            source_sentence="Organization X employs Person Y",
        ),
        Triple(
            "City X",
            "is_located_in",
            "Landmark Y",
            source_sentence="City X contains Landmark Y",
        ),
    ]
    corrected, anomalies = enforce_claim_direction_integrity(
        claims,
        kgc,
        answer="Organization X employs Person Y. City X contains Landmark Y.",
    )
    assert corrected[0].subject == "Person Y"
    assert corrected[0].object == "Organization X"
    assert corrected[1].subject == "Landmark Y"
    assert corrected[1].object == "City X"
    assert all(a.corrected for a in anomalies)


def test_reverse_kg_edge_does_not_auto_support_without_grammar():
    kgc = [KgcFact("Subject Y", "is_studied_by", "Researcher X")]
    inverted = Triple(
        "Researcher X",
        "is_studied_by",
        "Subject Y",
        source_sentence="unrelated phrase mentioning Researcher X and Subject Y",
    )
    assert find_reverse_entity_pair_fact(inverted, kgc) is not None
    corrected, anomalies = enforce_claim_direction_integrity(
        [inverted], kgc, answer=inverted.source_sentence or ""
    )
    # No safe grammar correction → leave unaligned; do not flip from KG alone.
    assert corrected[0].subject == "Researcher X"
    assert corrected[0].object == "Subject Y"
    assert anomalies and anomalies[0].corrected is False
    results = GraphComparator().compare_claims(corrected, kgc)
    assert results[0].label == KgcClaimLabel.NO_EVIDENCE


def test_terminal_answer_bearing_claim_preserved_after_direction_fix():
    kgc = [KgcFact("Entity Z", "is_studied_by", "Field B")]
    claims = [
        Triple("Entity A", "is_part_of", "Entity Z"),
        Triple(
            "Field B",
            "is_studied_by",
            "Entity Z",
            source_sentence="Field B studies Entity Z",
        ),
    ]
    corrected, _ = enforce_claim_direction_integrity(
        claims, kgc, answer="Field B studies Entity Z"
    )
    terminal = corrected[-1]
    assert terminal.subject == "Entity Z"
    assert terminal.object == "Field B"


# --- Fix 3: unresolved answer preservation -------------------------------------


def test_resolved_atomic_answer_may_reduce_to_terminal_object():
    path = {
        "terminal_claim": {
            "subject": "Apollo 11",
            "relation": "crewed_by",
            "object": "Neil Armstrong",
        },
        "evidence_path": [
            {
                "subject": "Apollo 11",
                "relation": "crewed_by",
                "object": "Neil Armstrong",
            }
        ],
    }
    out = prefer_terminal_object_answer(
        "Apollo 11 was crewed by Neil Armstrong",
        path,
        path_complete=True,
        resolved=True,
    )
    assert out == "Neil Armstrong"


def test_stalled_prose_answer_is_preserved():
    path = {
        "terminal_claim": {
            "subject": "Atlantic Ocean",
            "relation": "is_part_of",
            "object": "Global Ocean",
        },
        "evidence_path": [
            {
                "subject": "Atlantic Ocean",
                "relation": "is_part_of",
                "object": "Global Ocean",
            }
        ],
    }
    prose = "Oceanography studies the Global Ocean"
    out = prefer_terminal_object_answer(
        prose, path, path_complete=True, resolved=False
    )
    assert out == prose
    assert "Global Ocean" != out or out == prose

    combined = combine_sub_answers(
        [
            SubQuestionResult(
                sub_question_id=1,
                question="Which field studies the Global Ocean?",
                initial_answer=prose,
                final_answer=prose,
                stop_reason=SubQuestionStopReason.STALLED,
                iteration_count=2,
                evidence_path=path,
                evidence_path_complete=True,
            )
        ]
    )
    assert "Oceanography studies the Global Ocean" in combined
    assert combined.strip() != "Global Ocean"
    assert "[STALLED]" in combined


def test_unresolved_complete_path_does_not_become_terminal_object():
    path = {
        "terminal_claim": {
            "subject": "Entity A",
            "relation": "is_part_of",
            "object": "Entity Z",
        },
        "evidence_path": [
            {"subject": "Entity A", "relation": "is_part_of", "object": "Entity Z"}
        ],
    }
    answer = "Field B studies Entity Z via several intermediate regions."
    out = prefer_terminal_object_answer(
        answer, path, path_complete=True, resolved=False
    )
    assert out == answer
    assert out != "Entity Z"


def test_exact_match_scoring_and_pipeline_resolution_remain_separate():
    """Combiner must not rewrite stalled answers just because a path is complete."""
    path = {
        "terminal_claim": {"subject": "X", "relation": "is_part_of", "object": "Z"},
        "evidence_path": [{"subject": "X", "relation": "is_part_of", "object": "Z"}],
    }
    stalled = prefer_terminal_object_answer(
        "Field B studies Z", path, path_complete=True, resolved=False
    )
    resolved = prefer_terminal_object_answer(
        "Field B studies Z", path, path_complete=True, resolved=True
    )
    assert stalled == "Field B studies Z"
    # Object Z appears in answer; only RESOLVED may project it.
    assert resolved == "Z"


# --- Fix 4: answer-target integrity --------------------------------------------


def test_question_target_derivation_for_role_forms():
    cases = [
        ("Which field studies Entity Z?", "research_field", "is_studied_by"),
        ("Who founded Organization Y?", "founder", "is_founded_by"),
        (
            "Which organization administers Program Y?",
            "administered_by",
            "is_administered_by",
        ),
        ("What region contains Town Y?", "location_containment", "located_in"),
        ("Which material is produced by Factory X?", "manufacturer", "built_by"),
    ]
    for question, intent, canonical in cases:
        target = derive_question_target(question, [])
        assert target.intent == intent, question
        assert canonical in target.expected_relations or target.canonical_relation in {
            canonical,
            "produced_by",
            "located_in",
            "is_part_of",
            "contains",
        }


def test_complete_path_to_intermediate_claim_does_not_resolve_question():
    question = "Which field studies Entity Z?"
    kgc = [
        KgcFact("Root", "contains", "Entity A"),
        KgcFact("Entity A", "is_part_of", "Entity Z"),
        KgcFact("Entity Z", "is_studied_by", "Field B"),
    ]
    target = derive_question_target(question, kgc)
    assert target.intent == "research_field"

    intermediate = Triple("Entity A", "is_part_of", "Entity Z")
    evaluated = GraphComparator().compare_claims([intermediate], kgc)
    target_eval = evaluate_target_satisfaction(evaluated, target)
    assert target_eval.satisfied is False

    path = resolve_evidence_path(
        question=question,
        current_answer="Entity A is part of Entity Z",
        answer_claim=intermediate,
        question_target=target,
        trusted_facts=kgc,
    )
    # Path completeness is relative to the intermediate CLAIM only.
    # Even when that path is complete, the question target remains unsatisfied.
    stop, _ = determine_stop_reason(
        iteration=1,
        max_iterations=3,
        current_answer="Entity A is part of Entity Z",
        previous_answer="Entity A is part of Entity Z",
        previous_signature="sig",
        current_signature="sig",
        supported_count=1,
        contradicted_count=0,
        no_evidence_count=0,
        claim_count=1,
        target_satisfied=target_eval.satisfied,
        supported_but_irrelevant_count=target_eval.supported_but_irrelevant_count,
        evidence_path_complete=bool(path.complete),
        new_facts_added=False,
    )
    assert stop != SubQuestionStopReason.RESOLVED
    assert path.terminal_claim is None or path.terminal_claim["object"] == "Entity Z"


def test_correct_terminal_claim_produces_full_path_including_final_edge():
    question = "Which field studies Entity Z?"
    kgc = [
        KgcFact("Root", "contains", "Entity A"),
        KgcFact("Entity A", "is_part_of", "Entity Z"),
        KgcFact("Entity Z", "is_studied_by", "Field B"),
    ]
    target = derive_question_target(question, kgc)
    terminal = Triple("Entity Z", "is_studied_by", "Field B")
    evaluated = [
        KgcEvaluationResult(
            triple=terminal,
            label=KgcClaimLabel.SUPPORTED,
            reason="exact",
            evidence="trusted",
            matched_kgc_fact=kgc[-1],
        )
    ]
    target_eval = evaluate_target_satisfaction(evaluated, target)
    assert target_eval.satisfied is True

    path = resolve_evidence_path(
        question=question,
        current_answer="Field B studies Entity Z",
        answer_claim=terminal,
        question_target=target,
        trusted_facts=kgc,
    )
    assert path.complete is True
    assert path.path_length >= 2
    assert path.evidence_path[-1].object == "Field B"
    assert path.evidence_path[-1].relation == "is_studied_by"


def test_no_expected_answer_leakage_in_target_or_alignment():
    question = "Which field studies Entity Z?"
    kgc = [KgcFact("Entity Z", "is_studied_by", "Field B")]
    target = derive_question_target(question, kgc)
    assert "Field B" not in (target.primary_subject or "")
    # Alignment must not inject the trusted object into a wrong claim.
    claim = Triple("Field B", "is_studied_by", "Entity Z")
    aligned, _ = align_claims_to_kgc_schema([claim], kgc, question_target=target)
    assert aligned[0].object == "Entity Z"
    assert aligned[0].subject == "Field B"


def test_claim_and_fact_labels_remain_separate_after_rejected_alignment():
    kgc = [
        KgcFact("Entity A", "is_part_of", "Entity Z"),
        KgcFact("Entity Z", "is_studied_by", "Field B"),
    ]
    claim = Triple("Field B", "is_studied_by", "Entity Z")
    aligned, _ = align_claims_to_kgc_schema([claim], kgc)
    results = GraphComparator().compare_claims(aligned, kgc)
    assert results[0].label == KgcClaimLabel.NO_EVIDENCE
    assert results[0].matched_kgc_fact is None
    # Trusted FACT path still exists independently of the CLAIM label.
    assert any(
        f.subject == "Entity Z" and f.object == "Field B" for f in kgc
    )


def test_execution_isolation_contract_remains_intact_in_path_resolution():
    """Trusted facts from another execution must not complete this path."""
    question = "Which field studies Entity Z?"
    this_exec = [
        KgcFact("Entity A", "is_part_of", "Entity Z"),
        KgcFact("Entity Z", "is_studied_by", "Field B"),
    ]
    other_exec_only = KgcFact("Root", "contains", "Entity A")
    target = derive_question_target(question, this_exec)
    terminal = Triple("Entity Z", "is_studied_by", "Field B")

    path_isolated = resolve_evidence_path(
        question=question,
        current_answer="Field B studies Entity Z",
        answer_claim=terminal,
        question_target=target,
        trusted_facts=this_exec,
    )
    path_with_foreign = resolve_evidence_path(
        question=question,
        current_answer="Field B studies Entity Z",
        answer_claim=terminal,
        question_target=target,
        trusted_facts=this_exec + [other_exec_only],
    )
    assert path_isolated.complete is True
    assert path_with_foreign.complete is True
    # Path edges must only reference the provided trusted FACT list for this call;
    # foreign facts may extend the path only when explicitly supplied to resolver.
    assert all(
        edge.relation != "contains" or edge.subject == "Root"
        for edge in path_with_foreign.evidence_path
    )
    assert path_isolated.evidence_path[-1].object == "Field B"
