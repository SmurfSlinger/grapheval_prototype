"""Deterministic synthetic Rack R7 end-to-end pipeline tests."""

from __future__ import annotations

import json

from src.llm.mock_provider import MockProvider
from src.models import Example, KgcClaimLabel, SubQuestionStopReason
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner

CONTEXT = (
    "System Alpha uses Service A. "
    "Service A depends on Database B. "
    "Database B runs on Host C. "
    "Host C is located in Rack R7."
)

FACTS = [
    ("System Alpha", "uses", "Service A"),
    ("Service A", "depends_on", "Database B"),
    ("Database B", "runs_on", "Host C"),
    ("Host C", "located_in", "Rack R7"),
]

Q1 = "What service does System Alpha use?"
Q2 = "What database does the service used by System Alpha depend on?"
Q3 = "What host runs the database depended on by the service used by System Alpha?"
Q4 = (
    "Which rack contains the host that runs the database depended on by the "
    "service used by System Alpha?"
)
COMPOUND = f"{Q1} {Q2} {Q3} {Q4}"


class StageAwareRackProvider(MockProvider):
    """Exercises pipeline stages without always returning the final answer."""

    def __init__(self, *, mode: str = "happy") -> None:
        super().__init__()
        self.mode = mode
        self.stages_seen: list[str] = []

    def complete(self, prompt: str) -> str:
        lowered = prompt.lower()
        if "decompose the compound question" in lowered:
            self.stages_seen.append("decompose")
            if "which rack" in lowered and "what service" in lowered:
                questions = [
                    {"id": 1, "question": Q1},
                    {"id": 2, "question": Q2},
                    {"id": 3, "question": Q3},
                    {"id": 4, "question": Q4},
                ]
            elif "which rack" in lowered:
                questions = [{"id": 1, "question": Q4}]
            elif "what host" in lowered:
                questions = [{"id": 1, "question": Q3}]
            elif "what database" in lowered:
                questions = [{"id": 1, "question": Q2}]
            else:
                questions = [{"id": 1, "question": Q1}]
            return json.dumps({"questions": questions})

        if "extract factual triples from the trusted context below" in lowered or (
            "extract factual triples from the trusted context" in lowered
            and "sub-question" not in lowered
        ):
            self.stages_seen.append("context_facts")
            if "required header row" in lowered:
                lines = ["subject,relation,object,evidence"]
                for subject, relation, obj in FACTS:
                    lines.append(
                        f"{subject},{relation},{obj},Host C is located in Rack R7"
                    )
                return "\n".join(lines)
            return json.dumps(
                {
                    "triples": [
                        {
                            "subject": subject,
                            "relation": relation,
                            "object": obj,
                            "evidence": CONTEXT,
                        }
                        for subject, relation, obj in FACTS
                    ]
                }
            )

        if "relevant to answering" in lowered and "sub-question" in lowered:
            self.stages_seen.append("focused")
            if "required header row" in lowered:
                return "subject,relation,object,evidence\n"
            return json.dumps({"triples": []})

        if "project the compound answer" in lowered:
            self.stages_seen.append("project")
            # Keep projections faithful to whatever compound Answer(0) text is present.
            compound = ""
            if "compound answer(0):" in lowered:
                compound = (
                    prompt.split("Compound Answer(0):", 1)[-1]
                    .split("JSON:", 1)[0]
                    .strip()
                )
            compound_l = compound.lower()

            if self.mode in {"wrong_initial", "contradiction"}:
                return json.dumps({"answers": [{"id": 1, "answer": "Rack R9"}]})
            if self.mode == "no_evidence":
                return json.dumps({"answers": [{"id": 1, "answer": "blue"}]})

            if "service a" in compound_l and "database b" in compound_l:
                return json.dumps(
                    {
                        "answers": [
                            {"id": 1, "answer": "Service A"},
                            {"id": 2, "answer": "Database B"},
                            {"id": 3, "answer": "Host C"},
                            {"id": 4, "answer": "Rack R7"},
                        ]
                    }
                )
            if "service a" in compound_l:
                answer = "Service A"
            elif "database b" in compound_l:
                answer = "Database B"
            elif "host c" in compound_l and "rack" not in compound_l:
                answer = "Host C"
            elif "rack r7" in compound_l:
                answer = "Rack R7"
            else:
                answer = compound.strip() or "Rack R7"
            return json.dumps({"answers": [{"id": 1, "answer": answer}]})

        if self._is_claim_prompt(lowered):
            self.stages_seen.append("claims")
            prefer_csv = "required header row" in lowered
            if self.mode == "malformed_claim":
                if prefer_csv:
                    return (
                        "subject,relation,object,source_sentence\n"
                        "Host C,located_in,Rack R7,Rack R7\n"
                    )
                return json.dumps(
                    {
                        "triples": [
                            {
                                "subject": "Host C",
                                "relation": "located_in",
                                "object": None,
                                "source_sentence": "Rack R7",
                            },
                            {
                                "subject": "Host C",
                                "relation": "located_in",
                                "object": "Rack R7",
                                "source_sentence": "Rack R7",
                            },
                        ]
                    }
                )
            if self.mode == "contradiction":
                return self._claim_rows(
                    "Host C", "located_in", "Rack R9", prefer_csv=prefer_csv
                )
            if self.mode == "no_evidence":
                return self._claim_rows(
                    "Host C", "painted", "blue", prefer_csv=prefer_csv
                )
            if "service a" in lowered and "rack" not in lowered.split("answer:", 1)[-1]:
                # Prefer answer-local object for service questions.
                answer_tail = lowered.rsplit("answer:", 1)[-1]
                if "service a" in answer_tail and "rack" not in answer_tail:
                    return self._claim_rows(
                        "System Alpha", "uses", "Service A", prefer_csv=prefer_csv
                    )
            obj = "Rack R9" if "rack r9" in lowered else "Rack R7"
            if "database b" in lowered.rsplit("answer:", 1)[-1]:
                return self._claim_rows(
                    "Service A", "depends_on", "Database B", prefer_csv=prefer_csv
                )
            if "host c" in lowered.rsplit("answer:", 1)[-1] and "rack" not in lowered.rsplit(
                "answer:", 1
            )[-1]:
                return self._claim_rows(
                    "Database B", "runs_on", "Host C", prefer_csv=prefer_csv
                )
            return self._claim_rows(
                "Host C", "located_in", obj, prefer_csv=prefer_csv
            )

        if (
            "revise the graph-grounded answer" in lowered
            or "graph-grounded answer (answer n)" in lowered
            or "backtracking feedback" in lowered
        ):
            self.stages_seen.append("revise")
            return "Rack R7"

        if "answer only the current sub-question" in lowered:
            self.stages_seen.append("sub_answer")
            if self.mode in {"wrong_initial", "contradiction"}:
                return "Rack R9"
            if self.mode == "no_evidence":
                return "blue"
            if Q1.lower() in lowered:
                return "Service A"
            if Q2.lower() in lowered:
                return "Database B"
            if Q3.lower() in lowered:
                return "Host C"
            return "Rack R7"

        if "context:" in lowered and "question:" in lowered:
            self.stages_seen.append("answer")
            if self.mode in {"wrong_initial", "contradiction"}:
                return "Rack R9"
            if self.mode == "no_evidence":
                return "blue"
            # Compound must be checked before individual sub-question fragments.
            if "what service" in lowered and "which rack" in lowered:
                return "Service A. Database B. Host C. Rack R7."
            if Q1.lower() in lowered:
                return "Service A"
            if Q2.lower() in lowered:
                return "Database B"
            if Q3.lower() in lowered:
                return "Host C"
            return "Rack R7"

        raise AssertionError(f"Unhandled prompt stage:\n{prompt[:400]}")

    @staticmethod
    def _is_claim_prompt(lowered: str) -> bool:
        if "extract factual triples from the graph-grounded answer" in lowered:
            return True
        if "extract factual triples from the answer below as csv" in lowered:
            return True
        if "required header row" in lowered and "source_sentence" in lowered:
            return True
        return False

    @staticmethod
    def _claim_rows(
        subject: str, relation: str, obj: str, *, prefer_csv: bool
    ) -> str:
        if prefer_csv:
            return (
                "subject,relation,object,source_sentence\n"
                f"{subject},{relation},{obj},{obj}\n"
            )
        return json.dumps(
            {
                "triples": [
                    {
                        "subject": subject,
                        "relation": relation,
                        "object": obj,
                        "source_sentence": obj,
                    }
                ]
            }
        )


def _collect_labels(result) -> list[KgcClaimLabel]:
    return [
        ev.label
        for sq in result.sub_question_results
        for hist in sq.iteration_history
        for ev in hist.evaluated_claims
    ]


def _run(question: str, *, mode: str = "happy", initial: str | None = None):
    provider = StageAwareRackProvider(mode=mode)
    runner = DecomposedBacktrackingRunner(
        provider,
        max_iterations_per_sub_question=2,
        answer_0_mode="preset" if initial is not None else "generated_external_projected",
        clear_neo4j_before_run=False,
        neo4j_readback=False,
        require_neo4j=False,
    )
    example = Example(
        id=f"rack_{mode}",
        question=question,
        context=CONTEXT,
        initial_answer=initial,
    )
    assert not hasattr(example, "expected_answer")
    assert "expected_path" not in example.__dict__
    result = runner.run_example(example, attempt=1)
    return result, provider


def test_one_hop_service():
    result, provider = _run(Q1)
    assert "context_facts" in provider.stages_seen
    assert any(f.object == "Service A" for f in result.base_kgc_facts)
    assert result.combined_answer


def test_two_and_three_hop_questions():
    for question in (Q2, Q3):
        result, provider = _run(question)
        assert "context_facts" in provider.stages_seen
        assert result.base_kgc_facts
        assert result.sub_question_results


def test_four_hop_rack_r7():
    result, provider = _run(Q4)
    assert {f.object for f in result.base_kgc_facts} >= {
        "Service A",
        "Database B",
        "Host C",
        "Rack R7",
    }
    assert "Rack R7" in result.combined_answer
    assert "claims" in provider.stages_seen
    assert result.sub_question_results
    assert result.sub_question_results[0].stop_reason in {
        SubQuestionStopReason.RESOLVED,
        SubQuestionStopReason.MAX_ITERATIONS,
        SubQuestionStopReason.STALLED,
        SubQuestionStopReason.UNRESOLVED_NO_EVIDENCE,
        SubQuestionStopReason.UNRESOLVED_TARGET_NOT_SATISFIED,
    }
    assert result.trace is not None


def test_compound_question_path():
    result, provider = _run(COMPOUND)
    assert "decompose" in provider.stages_seen
    assert len(result.sub_question_results) >= 1
    blob = json.dumps(result.to_dict())
    assert "expected_answer" not in blob
    assert "expected_path" not in blob


def test_wrong_initial_answer_revision_path():
    result, provider = _run(Q4, mode="wrong_initial", initial="Rack R9")
    assert "claims" in provider.stages_seen
    labels = _collect_labels(result)
    assert KgcClaimLabel.CONTRADICTED in labels or "revise" in provider.stages_seen
    assert result.combined_answer


def test_malformed_claim_records_anomaly():
    result, provider = _run(Q4, mode="malformed_claim")
    assert "claims" in provider.stages_seen
    assert isinstance(result.structured_triple_anomalies, list)


def test_contradiction_and_no_evidence_labels():
    contradicted, provider = _run(Q4, mode="contradiction", initial="Rack R9")
    assert "claims" in provider.stages_seen
    labels = _collect_labels(contradicted)
    assert KgcClaimLabel.CONTRADICTED in labels

    missing, provider2 = _run(Q4, mode="no_evidence", initial="blue")
    assert "claims" in provider2.stages_seen
    labels2 = _collect_labels(missing)
    assert KgcClaimLabel.NO_EVIDENCE in labels2
