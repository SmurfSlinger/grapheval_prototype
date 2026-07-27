"""Deterministic depth-1-through-10 acceptance suite with distractors.

Uses a synthetic trusted graph and a stage-aware mock provider. Expected answers
and expected paths are used only for post-hoc assertions — never passed into the
pipeline or the evidence-path resolver.
"""

from __future__ import annotations

import json

import pytest

from src.llm.mock_provider import MockProvider
from src.models import Example, KgcFact, SubQuestionStopReason
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.evidence_path_resolver import resolve_evidence_path
from src.pipeline.execution_context import ExecutionScope
from src.pipeline.question_target import derive_question_target
from src.storage.neo4j_store import Neo4jStore, neo4j_status

MAIN_PATH: list[tuple[str, str, str]] = [
    ("Mission Alpha", "launched_by", "Rocket Beta"),
    ("Rocket Beta", "first_stage", "Stage Gamma"),
    ("Stage Gamma", "built_by", "Company Delta"),
    ("Company Delta", "headquartered_in", "City Epsilon"),
    ("City Epsilon", "located_in", "State Zeta"),
    ("State Zeta", "part_of", "Country Eta"),
    ("Country Eta", "led_by", "Person Theta"),
    ("Person Theta", "born_in", "Town Iota"),
    ("Town Iota", "located_in", "Region Kappa"),
    ("Region Kappa", "capital", "Terminal Lambda"),
]

DISTRACTORS: list[tuple[str, str, str]] = [
    # Sibling branch at depth 2.
    ("Rocket Beta", "first_stage", "Stage Rival"),
    ("Stage Rival", "built_by", "Company Rival"),
    # Similar relation at depth 4.
    ("Company Delta", "office_in", "City Decoy"),
    # Cycle at depth 5.
    ("City Epsilon", "near", "City Loop"),
    ("City Loop", "near", "City Epsilon"),
    # Disconnected path ending in the same object text.
    ("Orphan Root", "shortcut", "Terminal Lambda"),
    # Alternate branch with a plausible but incorrect terminal.
    ("Mission Alpha", "backup_vehicle", "Rocket Alternate"),
    ("Rocket Alternate", "first_stage", "Stage Alt"),
    ("Stage Alt", "built_by", "Company Alt"),
    ("Company Alt", "headquartered_in", "City Alt"),
    ("City Alt", "located_in", "State Alt"),
    ("State Alt", "part_of", "Country Alt"),
    ("Country Alt", "led_by", "Person Alt"),
    ("Person Alt", "born_in", "Town Alt"),
    ("Town Alt", "located_in", "Region Alt"),
    ("Region Alt", "capital", "Terminal Wrong"),
]

CONTEXT = (
    "Mission Alpha was launched by Rocket Beta. Rocket Beta's first stage is Stage Gamma; "
    "a sibling first stage is Stage Rival. Stage Gamma was built by Company Delta. "
    "Company Delta is headquartered in City Epsilon and also has an office in City Decoy. "
    "City Epsilon is located in State Zeta and is near City Loop, which is near City Epsilon. "
    "State Zeta is part of Country Eta. Country Eta is led by Person Theta. "
    "Person Theta was born in Town Iota. Town Iota is located in Region Kappa. "
    "Region Kappa's capital is Terminal Lambda. "
    "Orphan Root has a shortcut to Terminal Lambda. "
    "Mission Alpha also has backup vehicle Rocket Alternate whose chain ends at Terminal Wrong."
)

# Nested questions at designed depths 1..10. Answers/paths are scoring-only.
DEPTH_CASES: list[dict] = [
    {
        "depth": 1,
        "question": "Which vehicle launched Mission Alpha?",
        "answer": "Rocket Beta",
        "path_objects": ["Rocket Beta"],
    },
    {
        "depth": 2,
        "question": "What is the first stage of the rocket that launched Mission Alpha?",
        "answer": "Stage Gamma",
        "path_objects": ["Rocket Beta", "Stage Gamma"],
    },
    {
        "depth": 3,
        "question": "Which company built the first stage of the rocket that launched Mission Alpha?",
        "answer": "Company Delta",
        "path_objects": ["Rocket Beta", "Stage Gamma", "Company Delta"],
    },
    {
        "depth": 4,
        "question": "In which city is the company headquartered that built the first stage of the rocket that launched Mission Alpha?",
        "answer": "City Epsilon",
        "path_objects": ["Rocket Beta", "Stage Gamma", "Company Delta", "City Epsilon"],
    },
    {
        "depth": 5,
        "question": "Which state contains the city where the company that built the first stage of the rocket that launched Mission Alpha is headquartered?",
        "answer": "State Zeta",
        "path_objects": [
            "Rocket Beta",
            "Stage Gamma",
            "Company Delta",
            "City Epsilon",
            "State Zeta",
        ],
    },
    {
        "depth": 6,
        "question": "Which country contains the state that contains the city where the company that built the first stage of the rocket that launched Mission Alpha is headquartered?",
        "answer": "Country Eta",
        "path_objects": [
            "Rocket Beta",
            "Stage Gamma",
            "Company Delta",
            "City Epsilon",
            "State Zeta",
            "Country Eta",
        ],
    },
    {
        "depth": 7,
        "question": "Who leads the country that contains the state that contains the city where the company that built the first stage of the rocket that launched Mission Alpha is headquartered?",
        "answer": "Person Theta",
        "path_objects": [
            "Rocket Beta",
            "Stage Gamma",
            "Company Delta",
            "City Epsilon",
            "State Zeta",
            "Country Eta",
            "Person Theta",
        ],
    },
    {
        "depth": 8,
        "question": "In which town was the person born who leads the country that contains the state that contains the city where the company that built the first stage of the rocket that launched Mission Alpha is headquartered?",
        "answer": "Town Iota",
        "path_objects": [
            "Rocket Beta",
            "Stage Gamma",
            "Company Delta",
            "City Epsilon",
            "State Zeta",
            "Country Eta",
            "Person Theta",
            "Town Iota",
        ],
    },
    {
        "depth": 9,
        "question": "Which region contains the town where the person was born who leads the country that contains the state that contains the city where the company that built the first stage of the rocket that launched Mission Alpha is headquartered?",
        "answer": "Region Kappa",
        "path_objects": [
            "Rocket Beta",
            "Stage Gamma",
            "Company Delta",
            "City Epsilon",
            "State Zeta",
            "Country Eta",
            "Person Theta",
            "Town Iota",
            "Region Kappa",
        ],
    },
    {
        "depth": 10,
        "question": "What is the capital of the region that contains the town where the person was born who leads the country that contains the state that contains the city where the company that built the first stage of the rocket that launched Mission Alpha is headquartered?",
        "answer": "Terminal Lambda",
        "path_objects": [
            "Rocket Beta",
            "Stage Gamma",
            "Company Delta",
            "City Epsilon",
            "State Zeta",
            "Country Eta",
            "Person Theta",
            "Town Iota",
            "Region Kappa",
            "Terminal Lambda",
        ],
    },
]


def _trusted_facts() -> list[KgcFact]:
    return [
        KgcFact(subject, relation, obj, evidence=f"{subject} {relation} {obj}")
        for subject, relation, obj in MAIN_PATH + DISTRACTORS
    ]


class DepthAcceptanceProvider(MockProvider):
    """Exercises real pipeline stages without dumping the final answer for every prompt."""

    def __init__(self, *, question: str, answer: str) -> None:
        super().__init__()
        self.question = question
        self.answer = answer

    def complete(self, prompt: str) -> str:
        lowered = prompt.lower()
        if "decompose the compound question" in lowered:
            return json.dumps(
                {"questions": [{"id": 1, "question": self.question}]}
            )
        if "extract factual triples from the trusted context below" in lowered:
            return json.dumps(
                {
                    "triples": [
                        {
                            "subject": s,
                            "relation": r,
                            "object": o,
                            "evidence": f"{s} {r} {o}",
                        }
                        for s, r, o in MAIN_PATH + DISTRACTORS
                    ]
                }
            )
        if "project the compound answer" in lowered:
            return json.dumps({"answers": [{"id": 1, "answer": self.answer}]})
        if (
            "extract factual triples from the graph-grounded answer" in lowered
            or "extract factual triples from the answer" in lowered
            or ("sub-question defines what the answer must express" in lowered)
        ):
            # Emit only the terminal edge for the designed depth.
            depth = next(
                case["depth"]
                for case in DEPTH_CASES
                if case["question"] == self.question
            )
            subject = MAIN_PATH[depth - 1][0]
            relation = MAIN_PATH[depth - 1][1]
            obj = MAIN_PATH[depth - 1][2]
            # CSV claim extraction is the default path; JSON is the fallback.
            if "csv rows" in lowered or "subject,relation,object" in lowered:
                return (
                    "subject,relation,object,source_sentence\n"
                    f"{subject},{relation},{obj},{self.answer}\n"
                )
            return json.dumps(
                {
                    "triples": [
                        {
                            "subject": subject,
                            "relation": relation,
                            "object": obj,
                            "source_sentence": self.answer,
                        }
                    ]
                }
            )
        if "relevant to answering" in lowered and "sub-question" in lowered:
            return json.dumps({"triples": []})
        if "revise" in lowered or "backtracking feedback" in lowered:
            return self.answer
        if "context:" in lowered and "question:" in lowered:
            return self.answer
        return super().complete(prompt)


def _run_depth_case(case: dict):
    provider = DepthAcceptanceProvider(
        question=case["question"],
        answer=case["answer"],
    )
    runner = DecomposedBacktrackingRunner(
        provider,
        max_iterations_per_sub_question=3,
        answer_0_mode="generated_external_projected",
        clear_neo4j_before_run=False,
        neo4j_readback=False,
        require_neo4j=False,
    )
    return runner.run_example(
        Example(
            id=f"depth_{case['depth']:02d}",
            question=case["question"],
            context=CONTEXT,
        )
    )


@pytest.mark.parametrize("case", DEPTH_CASES, ids=lambda c: f"depth_{c['depth']}")
def test_synthetic_depth_resolves_with_complete_evidence_path(case):
    result = _run_depth_case(case)
    assert len(result.sub_question_results) == 1
    sub = result.sub_question_results[0]

    # Scoring-only expected answer — never fed to the pipeline above.
    assert case["answer"] in sub.final_answer
    assert sub.stop_reason == SubQuestionStopReason.RESOLVED
    assert sub.evidence_path_complete is True
    assert sub.evidence_path_length == case["depth"]
    assert sub.evidence_path is not None
    path = sub.evidence_path["evidence_path"]
    assert len(path) == case["depth"]
    assert [edge["object"] for edge in path] == case["path_objects"]
    assert path[0]["subject"] == "Mission Alpha"
    assert sub.final_answer.strip().rstrip(".") == case["answer"]
    assert not result.structured_triple_anomalies

    trusted = {(f.subject, f.relation, f.object) for f in _trusted_facts()}
    for edge in path:
        assert (edge["subject"], edge["relation"], edge["object"]) in trusted


def test_negative_missing_intermediate_edge():
    # Keep the terminal claim trusted; remove a linking intermediate edge.
    facts = [
        KgcFact(s, r, o)
        for s, r, o in MAIN_PATH
        if not (s == "Rocket Beta" and r == "first_stage")
    ]
    question = DEPTH_CASES[2]["question"]
    claim_subject, claim_relation, claim_object = MAIN_PATH[2]
    from src.models import Triple

    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Company Delta",
        answer_claim=Triple(claim_subject, claim_relation, claim_object),
        question_target=target,
        trusted_facts=facts,
    )
    assert result.complete is False
    assert result.failure_reason == "missing_intermediate_edge"


def test_negative_contradictory_final_edge_does_not_resolve_via_path():
    facts = _trusted_facts()
    from src.models import Triple

    question = DEPTH_CASES[0]["question"]
    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Rocket Alternate",
        answer_claim=Triple("Mission Alpha", "launched_by", "Rocket Alternate"),
        question_target=target,
        trusted_facts=facts,
    )
    # The alternate edge exists as a different relation; launched_by to Alternate
    # is not a trusted FACT.
    assert result.complete is False


def test_negative_ambiguous_branch():
    facts = [
        KgcFact("Mission Alpha", "launched_by", "Rocket Beta"),
        KgcFact("Mission Alpha", "launched_by", "Rocket Twin"),
        KgcFact("Rocket Beta", "first_stage", "Stage Gamma"),
        KgcFact("Rocket Twin", "first_stage", "Stage Gamma"),
        KgcFact("Stage Gamma", "built_by", "Company Delta"),
    ]
    from src.models import Triple

    question = DEPTH_CASES[2]["question"]
    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Company Delta",
        answer_claim=Triple("Stage Gamma", "built_by", "Company Delta"),
        question_target=target,
        trusted_facts=facts,
    )
    assert result.complete is False
    assert result.ambiguity == "sibling_branch_ambiguity"


def test_negative_disconnected_terminal_same_object_text():
    facts = _trusted_facts()
    from src.models import Triple

    question = DEPTH_CASES[9]["question"]
    target = derive_question_target(question, facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Terminal Lambda",
        answer_claim=Triple("Orphan Root", "shortcut", "Terminal Lambda"),
        question_target=target,
        trusted_facts=facts,
    )
    assert result.complete is False


def test_negative_correct_path_in_other_execution_only():
    """Same-named entity in another execution must not contribute edges."""
    other_scope_facts = [
        KgcFact("Mission Alpha", "launched_by", "Rocket Beta"),
        KgcFact("Rocket Beta", "first_stage", "Stage Gamma"),
    ]
    # Current execution is missing the linking edge.
    current_facts = [
        KgcFact("Stage Gamma", "built_by", "Company Delta"),
    ]
    from src.models import Triple

    question = DEPTH_CASES[2]["question"]
    target = derive_question_target(question, current_facts + other_scope_facts)
    result = resolve_evidence_path(
        question=question,
        current_answer="Company Delta",
        answer_claim=Triple("Stage Gamma", "built_by", "Company Delta"),
        question_target=target,
        trusted_facts=current_facts,  # only current execution
    )
    assert result.complete is False


def test_negative_wrong_model_answer_does_not_resolve():
    case = dict(DEPTH_CASES[2])
    case["answer"] = "Company Rival"
    # Provider will emit the wrong terminal; pipeline should not RESOLVE with a
    # complete main-path evidence trail to Company Delta.
    provider = DepthAcceptanceProvider(
        question=case["question"],
        answer=case["answer"],
    )

    class WrongTerminalProvider(DepthAcceptanceProvider):
        def complete(self, prompt: str) -> str:
            lowered = prompt.lower()
            if (
                "extract factual triples from the graph-grounded answer" in lowered
                or "extract factual triples from the answer" in lowered
                or ("sub-question defines what the answer must express" in lowered)
            ):
                if "csv rows" in lowered or "subject,relation,object" in lowered:
                    return (
                        "subject,relation,object,source_sentence\n"
                        "Stage Rival,built_by,Company Rival,Company Rival\n"
                    )
                return json.dumps(
                    {
                        "triples": [
                            {
                                "subject": "Stage Rival",
                                "relation": "built_by",
                                "object": "Company Rival",
                                "source_sentence": self.answer,
                            }
                        ]
                    }
                )
            return super().complete(prompt)

    result = DecomposedBacktrackingRunner(
        WrongTerminalProvider(question=case["question"], answer=case["answer"]),
        max_iterations_per_sub_question=2,
        answer_0_mode="generated_external_projected",
    ).run_example(
        Example(id="depth_wrong", question=case["question"], context=CONTEXT)
    )
    sub = result.sub_question_results[0]
    assert sub.stop_reason != SubQuestionStopReason.RESOLVED or (
        sub.evidence_path_complete
        and sub.evidence_path["evidence_path"][-1]["object"] == "Company Rival"
    )


def test_negative_qualifier_does_not_hijack_intent():
    question = (
        "In which town was the Mission Alpha crew member Person Theta born?"
    )
    # Person Theta is not a crew member of Mission Alpha in this graph, but the
    # qualifier must still not force crew_members intent.
    target = derive_question_target(question, _trusted_facts())
    assert target.intent == "birthplace"


@pytest.mark.live_neo4j
def test_live_same_named_entity_other_execution_isolated():
    if not (
        __import__("os").getenv("GRAPHEVAL_LIVE_NEO4J", "").strip().lower()
        in {"1", "true", "yes"}
    ):
        pytest.skip("Set GRAPHEVAL_LIVE_NEO4J=1")
    status = neo4j_status(required_for_this_route=True)
    if not status["connected"]:
        pytest.skip(f"Neo4j unavailable: {status.get('error')}")

    store = Neo4jStore()
    scope_a = ExecutionScope.begin("depth_exec_a")
    scope_b = ExecutionScope.begin("depth_exec_b")
    try:
        store.store_kgc_facts(
            scope_a,
            [KgcFact(s, r, o) for s, r, o in MAIN_PATH],
        )
        # Other execution has the same entity names but a wrong terminal.
        store.store_kgc_facts(
            scope_b,
            [
                KgcFact("Mission Alpha", "launched_by", "Rocket Beta"),
                KgcFact("Rocket Beta", "first_stage", "Stage Gamma"),
                KgcFact("Stage Gamma", "built_by", "Company Wrong"),
            ],
        )
        facts_a = store.get_kgc_facts(scope_a.execution_id)
        from src.models import Triple

        result = resolve_evidence_path(
            question=DEPTH_CASES[2]["question"],
            current_answer="Company Delta",
            answer_claim=Triple("Stage Gamma", "built_by", "Company Delta"),
            question_target=derive_question_target(
                DEPTH_CASES[2]["question"], facts_a
            ),
            trusted_facts=facts_a,
        )
        assert result.complete is True
        assert result.path_length == 3
        assert all(
            edge["object"] != "Company Wrong"
            for edge in result.to_dict()["evidence_path"]
        )
    finally:
        store.clear_execution(scope_a.execution_id)
        store.clear_execution(scope_b.execution_id)
        store.close()
