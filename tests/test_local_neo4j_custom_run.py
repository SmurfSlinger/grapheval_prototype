"""Custom-run smoke coverage without requiring live local services."""

from __future__ import annotations

import json

from src.llm.mock_provider import MockProvider
from src.models import Example, KgcFact
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner


CONTEXT = (
    "Test System Alpha uses Service A. Service A depends on Database B. "
    "Database B runs on Host C. Host C is located in Rack R7."
)
QUESTION = (
    "Which rack contains the host that runs the database depended on by the "
    "service used by Test System Alpha?"
)


class SyntheticSmokeProvider(MockProvider):
    """Deterministic test double; production pipeline contains no fixture answer."""

    def complete(self, prompt: str) -> str:
        lowered = prompt.lower()
        if "decompose the compound question" in lowered:
            return json.dumps({"questions": [{"id": 1, "question": QUESTION}]})
        if "extract factual triples from the trusted context below" in lowered:
            facts = [
                ("Test System Alpha", "uses", "Service A"),
                ("Service A", "depends_on", "Database B"),
                ("Database B", "runs_on", "Host C"),
                ("Host C", "located_in", "Rack R7"),
            ]
            return json.dumps(
                {
                    "triples": [
                        {
                            "subject": subject,
                            "relation": relation,
                            "object": obj,
                            "evidence": CONTEXT,
                        }
                        for subject, relation, obj in facts
                    ]
                }
            )
        if "project the compound answer" in lowered:
            return json.dumps({"answers": [{"id": 1, "answer": "Rack R7"}]})
        if "extract factual triples from the graph-grounded answer" in lowered:
            return json.dumps(
                {
                    "triples": [
                        {
                            "subject": "Host C",
                            "relation": "located_in",
                            "object": "Rack R7",
                            "source_sentence": "Rack R7",
                        }
                    ]
                }
            )
        if "relevant to answering" in lowered and "sub-question" in lowered:
            return json.dumps({"triples": []})
        if "context:" in lowered and "question:" in lowered:
            return "Rack R7"
        return super().complete(prompt)


def test_custom_context_uses_persisted_readback_and_keeps_claims_separate(
    monkeypatch,
):
    import src.pipeline.decomposed_backtracking_runner as runner_module

    stored_base: list[KgcFact] = []
    stored_claims = []
    stored_working = []
    clear_calls = 0

    def fake_clear(*, required: bool = False) -> bool:
        nonlocal clear_calls
        assert required is True
        clear_calls += 1
        return True

    def fake_store_base(example_id, facts, *, required=False):
        assert example_id == "synthetic_custom_smoke"
        assert required is True
        stored_base.extend(facts)
        return True

    def fake_readback(example_id, *, required=False):
        assert example_id == "synthetic_custom_smoke"
        assert required is True
        return list(stored_base)

    def fake_store_claims(
        example_id,
        iteration,
        evaluations,
        answer_stage=None,
        *,
        required=False,
    ):
        assert example_id == "synthetic_custom_smoke"
        assert required is True
        stored_claims.extend(evaluations)
        return True

    monkeypatch.setattr(runner_module, "clear_neo4j_if_enabled", fake_clear)
    monkeypatch.setattr(runner_module, "store_kgc_facts_if_enabled", fake_store_base)
    monkeypatch.setattr(runner_module, "read_kgc_facts_if_enabled", fake_readback)
    monkeypatch.setattr(runner_module, "store_kgc_claims_if_enabled", fake_store_claims)

    def fake_store_working(example_id, additions, *, required=False):
        assert required is True
        stored_working.extend(additions)
        return True

    monkeypatch.setattr(
        runner_module,
        "store_working_kgc_additions_if_enabled",
        fake_store_working,
    )

    result = DecomposedBacktrackingRunner(
        SyntheticSmokeProvider(),
        answer_0_mode="generated_external_projected",
        clear_neo4j_before_run=True,
        neo4j_readback=True,
        require_neo4j=True,
    ).run_example(
        Example(
            id="synthetic_custom_smoke",
            question=QUESTION,
            context=CONTEXT,
        )
    )

    assert clear_calls == 1
    assert len(stored_base) == 4
    assert "Rack R7" in result.combined_answer
    assert result.trace is not None
    assert result.trace.kgc_evaluation_source == "neo4j_readback"
    assert result.trace.neo4j_cleared_before_run is True
    assert stored_claims
    assert stored_working == []
    assert len(stored_base) == 4
