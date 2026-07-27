"""Trusted evidence-path resolver tests (no expected-answer leakage)."""

from __future__ import annotations

from src.models import KgcFact, Triple
from src.pipeline.evidence_path_resolver import resolve_evidence_path
from src.pipeline.question_target import derive_question_target


CHAIN = [
    KgcFact("Apollo 11", "crewed_by", "Neil Armstrong"),
    KgcFact("Neil Armstrong", "born_in", "Wapakoneta"),
    KgcFact("Wapakoneta", "located_in", "Ohio"),
]


def test_hop_two_birthplace_path_complete():
    question = "In which town was the Apollo 11 crew member Neil Armstrong born?"
    claim = Triple("Neil Armstrong", "born_in", "Wapakoneta")
    target = derive_question_target(question, CHAIN)
    result = resolve_evidence_path(
        question=question,
        current_answer="Wapakoneta",
        answer_claim=claim,
        question_target=target,
        trusted_facts=CHAIN,
    )
    assert result.complete is True
    assert result.path_length == 2
    assert result.start_entity == "Apollo 11"
    assert [edge.object for edge in result.evidence_path] == [
        "Neil Armstrong",
        "Wapakoneta",
    ]


def test_hop_three_containment_path_complete():
    question = "Which state contains the town where the Apollo 11 crew member Neil Armstrong was born?"
    # Prefer a question that mentions Apollo 11 so the root is identifiable.
    claim = Triple("Wapakoneta", "located_in", "Ohio")
    facts = CHAIN
    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Ohio",
        answer_claim=claim,
        question_target=target,
        trusted_facts=facts,
    )
    assert result.complete is True
    assert result.path_length == 3
    assert result.start_entity == "Apollo 11"


def test_missing_intermediate_edge_is_incomplete():
    question = "In which town was the Apollo 11 crew member Neil Armstrong born?"
    claim = Triple("Neil Armstrong", "born_in", "Wapakoneta")
    # Apollo 11 is present but not connected to the terminal subject.
    facts = [
        KgcFact("Apollo 11", "launched_from", "Kennedy Space Center"),
        KgcFact("Neil Armstrong", "born_in", "Wapakoneta"),
    ]
    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Wapakoneta",
        answer_claim=claim,
        question_target=target,
        trusted_facts=facts,
    )
    assert result.complete is False
    assert result.failure_reason == "missing_intermediate_edge"


def test_disconnected_terminal_text_is_incomplete():
    question = "In which town was the Apollo 11 crew member Neil Armstrong born?"
    # Same object text, but not connected through trusted FACTS from the root.
    claim = Triple("Some Other Person", "born_in", "Wapakoneta")
    facts = CHAIN + [claim]
    # claim is a Triple, need KgcFact for facts list
    facts = CHAIN + [
        KgcFact("Some Other Person", "born_in", "Wapakoneta"),
    ]
    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Wapakoneta",
        answer_claim=claim,
        question_target=target,
        trusted_facts=facts,
    )
    assert result.complete is False


def test_sibling_branch_ambiguity_detected():
    question = "In which town was a Mission Alpha crew member born?"
    facts = [
        KgcFact("Mission Alpha", "branch_a", "Mid One"),
        KgcFact("Mission Alpha", "branch_b", "Mid Two"),
        KgcFact("Mid One", "links_to", "Person A"),
        KgcFact("Mid Two", "links_to", "Person A"),
        KgcFact("Person A", "born_in", "Town X"),
    ]
    claim = Triple("Person A", "born_in", "Town X")
    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Town X",
        answer_claim=claim,
        question_target=target,
        trusted_facts=facts,
    )
    assert result.complete is False
    assert result.ambiguity == "sibling_branch_ambiguity"


def test_cycle_does_not_invent_a_path():
    question = "Where is City Epsilon?"
    facts = [
        KgcFact("City Epsilon", "near", "City Zeta"),
        KgcFact("City Zeta", "near", "City Epsilon"),
        KgcFact("City Epsilon", "located_in", "State Zeta"),
    ]
    claim = Triple("City Epsilon", "located_in", "State Zeta")
    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="State Zeta",
        answer_claim=claim,
        question_target=target,
        trusted_facts=facts,
    )
    assert result.complete is True
    assert result.path_length == 1


def test_claims_are_not_accepted_as_evidence():
    # Only FACTS are passed in; the resolver has no CLAIM input by design.
    question = "In which town was the Apollo 11 crew member Neil Armstrong born?"
    claim = Triple("Neil Armstrong", "born_in", "Wapakoneta")
    target = derive_question_target(question, CHAIN)
    result = resolve_evidence_path(
        question=question,
        current_answer="Wapakoneta",
        answer_claim=claim,
        question_target=target,
        trusted_facts=CHAIN,
    )
    assert all(
        isinstance(edge.subject, str) and isinstance(edge.relation, str)
        for edge in result.evidence_path
    )
