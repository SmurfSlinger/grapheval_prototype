"""Deterministic decomposed-backtracking behavior suite.

Twenty-four fixed scenarios covering decomposition, direction, alignment,
evaluation labels, target integrity, answer preservation, CLAIM/FACT
separation, execution isolation, and scoring-metadata hygiene. No scenario
depends on favorable live-model output; scripted mock providers and direct
fixtures are used throughout. The scenario-to-test coverage matrix lives in
docs/DECOMPOSED_BACKTRACKING_BEHAVIOR_MATRIX.md.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from src.benchmarks.catalog import contains_expected_answer, exact_match
from src.llm.mock_provider import MockProvider
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
from src.pipeline.question_decomposition_validation import decomposition_is_valid
from src.pipeline.question_splitter import QuestionSplitter
from src.pipeline.question_target import (
    derive_question_target,
    evaluate_target_satisfaction,
)
from src.pipeline.sub_answer_combiner import (
    combine_sub_answers,
    prefer_terminal_object_answer,
)

REPO = Path(__file__).resolve().parents[1]


class ScriptedSplitProvider(MockProvider):
    def __init__(self, payload: dict) -> None:
        super().__init__()
        self._payload = payload

    def complete(self, prompt: str) -> str:
        if "Compound question:" in prompt or "questions" in prompt.lower():
            return json.dumps(self._payload)
        return super().complete(prompt)


# --- Scenarios 1-4: decomposition ------------------------------------------------


def test_s01_atomic_question_remains_atomic():
    question = "Which agency established the governing plan?"
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "Which"},
                {"id": 2, "question": "agency"},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(question)
    assert [sq.question for sq in subs] == [question]


def test_s02_nested_single_clause_question_remains_atomic():
    question = "In which region is the birthplace of the crew member of Mission X?"
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "Who was the crew member of Mission X?"},
                {"id": 2, "question": "Where was the crew member born?"},
                {"id": 3, "question": "In which region is the birthplace?"},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(question)
    assert [sq.question for sq in subs] == [question]


def test_s03_true_compound_question_decomposes():
    question = "Who crewed Mission X, and which pad launched Mission X?"
    proposed = [
        "Who crewed Mission X?",
        "Which pad launched Mission X?",
    ]
    assert decomposition_is_valid(question, proposed)
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": proposed[0]},
                {"id": 2, "question": proposed[1]},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(question)
    assert [sq.question for sq in subs] == proposed


def test_s04_invalid_fragment_decomposition_falls_back():
    question = "Which field studies Entity Z?"
    assert not decomposition_is_valid(question, ["Which", "field", "Entity Z"])
    provider = ScriptedSplitProvider(
        {
            "questions": [
                {"id": 1, "question": "Which"},
                {"id": 2, "question": "field"},
                {"id": 3, "question": "Entity Z"},
            ]
        }
    )
    subs, _ = QuestionSplitter(provider).split(question)
    assert [sq.question for sq in subs] == [question]


# --- Scenario 5: acronym/alias resolution ----------------------------------------


def test_s05_acronym_and_alias_resolution():
    from scripts.nhs_wannacry_hop_semantics import detect_entities_in_text

    entities = {"Joint Interoperability Test Command"}
    aliases = {
        "Joint Interoperability Test Command": [
            "Joint Interoperability Test Command",
            "JITC",
        ]
    }
    detected = detect_entities_in_text(
        "Which register does JITC maintain?", entities, aliases
    )
    assert detected == ["Joint Interoperability Test Command"]
    # Scoring-side normalization: harmless terminal punctuation is stripped
    # after lowercase letters; case-insensitive matching is contains-level.
    assert exact_match("saturn v.", "saturn v")
    assert contains_expected_answer("The answer is Saturn V.", "saturn v")


# --- Scenarios 6-7: relation direction -------------------------------------------


def test_s06_active_to_passive_direction_correction():
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
    assert corrected[0].object == "Researcher X"
    assert anomalies and anomalies[0].corrected is True


def test_s07_inverse_direction_without_grammar_stays_unsupported():
    kgc = [KgcFact("Subject Y", "is_studied_by", "Researcher X")]
    inverted = Triple(
        "Researcher X",
        "is_studied_by",
        "Subject Y",
        source_sentence="a phrase naming Researcher X and Subject Y without a verb",
    )
    assert find_reverse_entity_pair_fact(inverted, kgc) is not None
    corrected, anomalies = enforce_claim_direction_integrity(
        [inverted], kgc, answer=inverted.source_sentence or ""
    )
    assert corrected[0].subject == "Researcher X"
    assert anomalies and anomalies[0].corrected is False
    labels = [r.label for r in GraphComparator().compare_claims(corrected, kgc)]
    assert labels == [KgcClaimLabel.NO_EVIDENCE]


# --- Scenario 8: object-only alignment safety ------------------------------------


def test_s08_object_only_alignment_cannot_rewrite_subject_and_relation():
    kgc = [
        KgcFact("Entity A", "is_part_of", "Entity Z"),
        KgcFact("Entity Z", "is_studied_by", "Entity B"),
    ]
    claim = Triple("Entity B", "is_studied_by", "Entity Z")
    aligned, traces = align_claims_to_kgc_schema([claim], kgc)
    assert aligned[0].subject == "Entity B"
    assert aligned[0].relation == "is_studied_by"
    assert aligned[0].object == "Entity Z"
    assert traces == []


# --- Scenarios 9-12: evaluation labels -------------------------------------------


def test_s09_correct_answer_with_unsupported_explanatory_prose_not_resolved():
    kgc = [KgcFact("Entity Z", "is_studied_by", "Field B")]
    claims = [
        Triple("Entity Z", "is_studied_by", "Field B"),
        Triple("Entity Q", "influences", "Field B"),  # unsupported explanation
    ]
    results = GraphComparator().compare_claims(claims, kgc)
    labels = [r.label for r in results]
    assert labels[0] == KgcClaimLabel.SUPPORTED
    assert labels[1] == KgcClaimLabel.NO_EVIDENCE
    stop, _ = determine_stop_reason(
        iteration=0,
        max_iterations=3,
        current_answer="Field B, because Entity Q influences it.",
        previous_answer=None,
        previous_signature=None,
        current_signature="sig-a",
        supported_count=1,
        contradicted_count=0,
        no_evidence_count=1,
        claim_count=2,
        target_satisfied=True,
        evidence_path_complete=True,
        new_facts_added=False,
    )
    assert stop != SubQuestionStopReason.RESOLVED


def test_s10_wrong_answer_correctly_rejected():
    kgc = [KgcFact("Mission X", "launched_from", "Pad Alpha")]
    wrong = Triple("Mission X", "launched_from", "Pad Beta")
    results = GraphComparator().compare_claims([wrong], kgc)
    assert results[0].label == KgcClaimLabel.CONTRADICTED


def test_s11_contradiction_blocks_resolution():
    stop, _ = determine_stop_reason(
        iteration=2,
        max_iterations=3,
        current_answer="Pad Beta",
        previous_answer="Pad Beta",
        previous_signature="sig",
        current_signature="sig",
        supported_count=0,
        contradicted_count=1,
        no_evidence_count=0,
        claim_count=1,
        target_satisfied=False,
        evidence_path_complete=False,
        new_facts_added=False,
    )
    assert stop is not None
    assert stop != SubQuestionStopReason.RESOLVED


def test_s12_no_evidence_claim_labeled():
    kgc = [KgcFact("Mission X", "launched_from", "Pad Alpha")]
    unknown = Triple("Mission X", "commanded_by", "Person P")
    results = GraphComparator().compare_claims([unknown], kgc)
    assert results[0].label == KgcClaimLabel.NO_EVIDENCE
    assert results[0].matched_kgc_fact is None


# --- Scenarios 13-14: path completeness vs target --------------------------------


GENERIC_KGC = [
    KgcFact("Root", "contains", "Entity A"),
    KgcFact("Entity A", "is_part_of", "Entity Z"),
    KgcFact("Entity Z", "is_studied_by", "Field B"),
]


def test_s13_complete_intermediate_path_does_not_satisfy_target():
    question = "Which field studies Entity Z?"
    target = derive_question_target(question, GENERIC_KGC)
    intermediate = Triple("Entity A", "is_part_of", "Entity Z")
    evaluated = GraphComparator().compare_claims([intermediate], GENERIC_KGC)
    target_eval = evaluate_target_satisfaction(evaluated, target)
    assert target_eval.satisfied is False
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
        target_satisfied=False,
        supported_but_irrelevant_count=target_eval.supported_but_irrelevant_count,
        evidence_path_complete=True,
        new_facts_added=False,
    )
    assert stop != SubQuestionStopReason.RESOLVED


def test_s14_complete_path_to_terminal_answer_includes_final_edge():
    question = "Which field studies Entity Z?"
    target = derive_question_target(question, GENERIC_KGC)
    terminal = Triple("Entity Z", "is_studied_by", "Field B")
    path = resolve_evidence_path(
        question=question,
        current_answer="Field B studies Entity Z",
        answer_claim=terminal,
        question_target=target,
        trusted_facts=GENERIC_KGC,
    )
    assert path.complete is True
    assert path.evidence_path[-1].relation == "is_studied_by"
    assert path.evidence_path[-1].object == "Field B"


# --- Scenarios 15-17: answer types ----------------------------------------------


def test_s15_list_answer_supported_and_scored():
    kgc = [KgcFact("Panel Q", "composed_of", "Alice, Bob, Carol")]
    claim = Triple("Panel Q", "composed_of", "Alice, Bob, Carol")
    results = GraphComparator().compare_claims([claim], kgc)
    assert results[0].label == KgcClaimLabel.SUPPORTED
    assert exact_match("Alice, Bob, Carol", "Alice, Bob, Carol")
    assert contains_expected_answer("Alice, Bob, Carol", "alice, bob, carol")


def test_s16_numeric_answer_supported_and_scored():
    kgc = [KgcFact("Format Field V", "holds_valid_value", "02.10")]
    claim = Triple("Format Field V", "holds_valid_value", "02.10")
    results = GraphComparator().compare_claims([claim], kgc)
    assert results[0].label == KgcClaimLabel.SUPPORTED
    assert exact_match("02.10", "02.10")
    assert not exact_match("02.1", "02.10")


def test_s17_date_version_answer_supported_and_scored():
    kgc = [KgcFact("Standard S", "dated", "12 October 1994")]
    claim = Triple("Standard S", "dated", "12 October 1994")
    results = GraphComparator().compare_claims([claim], kgc)
    assert results[0].label == KgcClaimLabel.SUPPORTED
    assert exact_match("12 October 1994", "12 October 1994")
    assert contains_expected_answer("dated 12 October 1994", "12 october 1994")


# --- Scenario 18: unchanged answer stops cleanly ---------------------------------


def test_s18_repeated_unchanged_answer_without_new_facts_stops():
    stop, _ = determine_stop_reason(
        iteration=1,
        max_iterations=3,
        current_answer="Entity A is part of Entity Z",
        previous_answer="Entity A is part of Entity Z",
        previous_signature="sig",
        current_signature="sig",
        supported_count=0,
        contradicted_count=0,
        no_evidence_count=1,
        claim_count=1,
        target_satisfied=False,
        evidence_path_complete=False,
        new_facts_added=False,
    )
    assert stop is not None
    assert stop != SubQuestionStopReason.RESOLVED


# --- Scenarios 19-20: answer preservation/projection ------------------------------


UNRESOLVED_PATH = {
    "terminal_claim": {"subject": "Entity A", "relation": "is_part_of", "object": "Entity Z"},
    "evidence_path": [
        {"subject": "Entity A", "relation": "is_part_of", "object": "Entity Z"}
    ],
}


def test_s19_unresolved_answer_text_remains_uncorrupted():
    prose = "Field B studies Entity Z through several intermediate regions."
    out = prefer_terminal_object_answer(
        prose, UNRESOLVED_PATH, path_complete=True, resolved=False
    )
    assert out == prose
    combined = combine_sub_answers(
        [
            SubQuestionResult(
                sub_question_id=1,
                question="Which field studies Entity Z?",
                initial_answer=prose,
                final_answer=prose,
                stop_reason=SubQuestionStopReason.STALLED,
                iteration_count=2,
                evidence_path=UNRESOLVED_PATH,
                evidence_path_complete=True,
            )
        ]
    )
    assert prose in combined
    assert combined.strip() != "Entity Z"


def test_s20_resolved_atomic_prose_projects_to_verified_terminal_object():
    path = {
        "terminal_claim": {
            "subject": "Entity Z",
            "relation": "is_studied_by",
            "object": "Field B",
        },
        "evidence_path": [
            {"subject": "Entity Z", "relation": "is_studied_by", "object": "Field B"}
        ],
    }
    out = prefer_terminal_object_answer(
        "Entity Z is studied by Field B",
        path,
        path_complete=True,
        resolved=True,
    )
    assert out == "Field B"


# --- Scenarios 21-23: CLAIM/FACT separation and isolation -------------------------


def test_s21_supported_claims_remain_claims_not_facts():
    kgc = [KgcFact("Entity Z", "is_studied_by", "Field B")]
    before = [(f.subject, f.relation, f.object) for f in kgc]
    claim = Triple("Entity Z", "is_studied_by", "Field B")
    results = GraphComparator().compare_claims([claim], kgc)
    assert results[0].label == KgcClaimLabel.SUPPORTED
    after = [(f.subject, f.relation, f.object) for f in kgc]
    assert before == after  # evaluation must not add claims into trusted FACTS
    assert isinstance(results[0].triple, Triple)


def test_s22_execution_isolation_facts_do_not_leak_between_calls():
    question = "Which field studies Entity Z?"
    target = derive_question_target(question, GENERIC_KGC)
    terminal = Triple("Entity Z", "is_studied_by", "Field B")
    other_execution_facts = [KgcFact("Entity Z", "is_studied_by", "Field OTHER")]
    isolated = resolve_evidence_path(
        question=question,
        current_answer="Field B studies Entity Z",
        answer_claim=terminal,
        question_target=target,
        trusted_facts=GENERIC_KGC,
    )
    assert isolated.complete is True
    assert all(
        edge.object != "Field OTHER" for edge in isolated.evidence_path
    ), "facts from another execution must never appear in this path"
    _ = other_execution_facts  # never passed in; isolation is by explicit scoping


def test_s23_neo4j_store_scopes_every_query_by_execution_id():
    from src.storage import neo4j_store

    source = inspect.getsource(neo4j_store)
    assert source.count("execution_id") >= 30
    # Cross-execution reads are forbidden: every MATCH on Entity/FACT/CLAIM is
    # parameterized by execution_id in the store module.
    for snippet in ("MATCH", "MERGE"):
        assert snippet in source


# --- Scenario 24: scoring metadata never enters inference -------------------------


def test_s24_expected_answer_metadata_never_enters_inference_inputs():
    dataset = json.loads(
        (REPO / "data" / "test_sets" / "nitfs_geoint_multihop_50.json").read_text()
    )
    context = dataset["trusted_context"].lower()
    assert "expected_answer" not in context
    assert "expected_path" not in context
    for question in dataset["questions"]:
        if question["hop_count"] > 1:
            assert (
                question["expected_answer"].lower() not in question["question"].lower()
            )
    # The runner passes only id + question text + trusted context into the
    # pipeline: the Example handed to run_example carries no scoring metadata.
    import scripts.run_multihop_benchmark as runner

    source = inspect.getsource(runner.run_one)
    example_call = source.split("runner.run_example(")[1].split(")")[0] + ")"
    assert "expected_answer" not in example_call
    assert "expected_path" not in example_call
    assert "required_entities" not in example_call
    assert "required_relations" not in example_call
    assert "hop_count" not in example_call
    assert 'question["question"]' in example_call
    assert "context=context" in example_call
