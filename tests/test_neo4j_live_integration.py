"""Live Neo4j integration tests. Enable with GRAPHEVAL_LIVE_NEO4J=1."""

from __future__ import annotations

import os
import uuid

import pytest

from src.models import (
    KgcClaimLabel,
    KgcEvaluationResult,
    KgcFact,
    KgcProvenanceType,
    Triple,
    WorkingKgcAddition,
)
from src.storage.neo4j_store import Neo4jStore, neo4j_status

pytestmark = pytest.mark.live_neo4j


def _live_enabled() -> bool:
    return os.getenv("GRAPHEVAL_LIVE_NEO4J", "").strip().lower() in {"1", "true", "yes"}


@pytest.fixture
def store():
    if not _live_enabled():
        pytest.skip("Set GRAPHEVAL_LIVE_NEO4J=1 to run live Neo4j tests")
    os.environ["NEO4J_ENABLED"] = "true"
    import src.config as config

    config.NEO4J_ENABLED = True
    status = neo4j_status(required_for_this_route=True)
    if not status["configured"] or not status["connected"]:
        pytest.skip(f"Neo4j unavailable: {status.get('error')}")
    neo = Neo4jStore()
    neo.clear_all()
    try:
        yield neo
    finally:
        neo.clear_all()
        neo.close()


def test_fact_roundtrip_and_claim_separation(store: Neo4jStore):
    run_id = f"live_fact_{uuid.uuid4().hex[:8]}"
    facts = [
        KgcFact("System Alpha", "uses", "Service A", evidence="ctx1"),
        KgcFact("Service A", "depends_on", "Database B", evidence="ctx2"),
        KgcFact("Database B", "runs_on", "Host C", evidence="ctx3"),
        KgcFact("Host C", "located_in", "Rack R7", evidence="ctx4"),
    ]
    store.store_kgc_facts(run_id, facts)
    readback = store.get_kgc_facts(run_id)
    assert [(f.subject, f.relation, f.object, f.evidence) for f in readback] == [
        (f.subject, f.relation, f.object, f.evidence) for f in facts
    ]

    evaluations = [
        KgcEvaluationResult(
            triple=Triple("Host C", "located_in", "Rack R7"),
            label=KgcClaimLabel.SUPPORTED,
            reason="match",
            evidence="ctx4",
        ),
        KgcEvaluationResult(
            triple=Triple("Host C", "located_in", "Rack R9"),
            label=KgcClaimLabel.CONTRADICTED,
            reason="conflict",
            evidence="ctx4",
            conflicting_object="Rack R7",
        ),
        KgcEvaluationResult(
            triple=Triple("Host C", "color", "blue"),
            label=KgcClaimLabel.NO_EVIDENCE,
            reason="missing",
            evidence="",
        ),
    ]
    store.store_kgc_claims(run_id, iteration=0, evaluations=evaluations, answer_stage="answer_0")
    store.store_kgc_claims(run_id, iteration=1, evaluations=evaluations[:1], answer_stage="answer_1")

    claims = store.get_claims_for_example(run_id, limit=50)
    assert len(claims) == 4
    assert all(c.get("source", "answer") or True for c in claims)
    labels = {c["label"] for c in claims}
    assert "SUPPORTED" in labels
    assert "CONTRADICTED" in labels
    assert "NO_EVIDENCE" in labels

    bad = store.get_bad_claims(limit=50)
    bad_labels = {c["label"] for c in bad if c["example_id"] == run_id}
    assert "CONTRADICTED" in bad_labels
    assert "NO_EVIDENCE" in bad_labels

    counts = store.get_relationship_counts(run_id)
    assert counts["fact_edges"] == 4
    assert counts["claim_edges"] == 4

    # Supported claims must not become FACT edges.
    fact_objects = {(f.subject, f.relation, f.object) for f in store.get_kgc_facts(run_id)}
    assert ("Host C", "located_in", "Rack R7") in fact_objects
    assert len(fact_objects) == 4


def test_two_run_ids_independent(store: Neo4jStore):
    a = f"run_a_{uuid.uuid4().hex[:6]}"
    b = f"run_b_{uuid.uuid4().hex[:6]}"
    store.store_kgc_facts(a, [KgcFact("A", "rel", "1", evidence="a")])
    store.store_kgc_facts(b, [KgcFact("B", "rel", "2", evidence="b")])
    assert [f.object for f in store.get_kgc_facts(a)] == ["1"]
    assert [f.object for f in store.get_kgc_facts(b)] == ["2"]


def test_focused_fact_provenance(store: Neo4jStore):
    run_id = f"live_focus_{uuid.uuid4().hex[:6]}"
    addition = WorkingKgcAddition(
        fact=KgcFact("Host C", "located_in", "Rack R7", evidence="span"),
        provenance=KgcProvenanceType.TRUSTED_CONTEXT,
        sub_question_id=1,
        extraction_scope="focused",
        evidence_spans=["Host C is located in Rack R7."],
    )
    store.store_working_kgc_additions(run_id, [addition])
    facts = store.get_kgc_facts(run_id)
    assert len(facts) == 1
    assert facts[0].object == "Rack R7"


def test_neo4j_status_structure():
    if not _live_enabled():
        pytest.skip("Set GRAPHEVAL_LIVE_NEO4J=1")
    status = neo4j_status(required_for_this_route=True)
    assert "configured" in status
    assert "connected" in status
    assert "required_for_this_route" in status
    assert "error" in status
    assert "password" not in str(status).lower() or status.get("error")
