"""Live Neo4j execution-isolation tests. Enable with GRAPHEVAL_LIVE_NEO4J=1.

These run against the real recreated Neo4j instance (no storage monkeypatching)
and prove the Phase 2 execution-isolation contract:

 1. Two executions containing "Apollo 11" create distinct nodes.
 2. Repeating one benchmark question does not mix the two attempts.
 3. FACT readback returns only the requested execution.
 4. CLAIM readback returns only the requested execution.
 5. NO_EVIDENCE is returned by the bad-claim query.
 6. CONTRADICTED is returned by the bad-claim query.
 7. Supported CLAIMS remain CLAIMS.
 8. Focused FACT provenance survives round-trip.
 9. Derived FACT provenance survives round-trip.
10. Clearing one execution leaves another intact.
11. API-reported relationship counts match direct Cypher counts.
12. Restarting Neo4j preserves the named-volume data.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time

import pytest

from src.models import (
    KgcClaimLabel,
    KgcEvaluationResult,
    KgcFact,
    KgcProvenanceType,
    Triple,
    WorkingKgcAddition,
)
from src.pipeline.execution_context import ExecutionScope, new_execution_id
from src.storage.neo4j_store import Neo4jStore, neo4j_status

pytestmark = pytest.mark.live_neo4j


def _live_enabled() -> bool:
    return os.getenv("GRAPHEVAL_LIVE_NEO4J", "").strip().lower() in {"1", "true", "yes"}


class _Harness:
    """Tracks executions created by a test so teardown removes only those."""

    def __init__(self, store: Neo4jStore) -> None:
        self.store = store
        self.execution_ids: list[str] = []

    def scope(
        self,
        example_id: str,
        *,
        benchmark_id: str | None = None,
        question_id: str | None = None,
    ) -> ExecutionScope:
        scope = ExecutionScope.begin(
            example_id,
            benchmark_id=benchmark_id,
            question_id=question_id,
        )
        self.execution_ids.append(scope.execution_id)
        return scope


@pytest.fixture
def harness():
    if not _live_enabled():
        pytest.skip("Set GRAPHEVAL_LIVE_NEO4J=1 to run live Neo4j tests")
    os.environ["NEO4J_ENABLED"] = "true"
    import src.config as config

    config.NEO4J_ENABLED = True
    status = neo4j_status(required_for_this_route=True)
    if not status["configured"] or not status["connected"]:
        pytest.skip(f"Neo4j unavailable: {status.get('error')}")
    neo = Neo4jStore()
    h = _Harness(neo)
    try:
        yield h
    finally:
        # Execution-scoped cleanup: never a full-graph delete. Uses h.store so
        # tests that reconnect (e.g. the restart test) clean up correctly.
        for execution_id in h.execution_ids:
            h.store.clear_execution(execution_id)
        h.store.close()


def _apollo_facts() -> list[KgcFact]:
    return [
        KgcFact("Apollo 11", "crewed_by", "Neil Armstrong", evidence="ctx crew"),
        KgcFact("Neil Armstrong", "born_in", "Wapakoneta", evidence="ctx birth"),
    ]


def _entity_nodes(store: Neo4jStore, name: str) -> list[dict]:
    with store._session() as session:
        result = session.run(
            "MATCH (e:Entity {name: $name}) RETURN e.execution_id AS execution_id",
            name=name,
        )
        return [dict(record) for record in result]


def test_two_executions_create_distinct_apollo_nodes(harness: _Harness):
    """(1) Two executions containing 'Apollo 11' create distinct Entity nodes."""
    scope_a = harness.scope("apollo_hop_011")
    scope_b = harness.scope("apollo_hop_011")
    assert scope_a.execution_id != scope_b.execution_id

    harness.store.store_kgc_facts(scope_a, _apollo_facts())
    harness.store.store_kgc_facts(scope_b, _apollo_facts())

    nodes = [
        record
        for record in _entity_nodes(harness.store, "Apollo 11")
        if record["execution_id"] in {scope_a.execution_id, scope_b.execution_id}
    ]
    assert len(nodes) == 2
    assert {record["execution_id"] for record in nodes} == {
        scope_a.execution_id,
        scope_b.execution_id,
    }


def test_repeated_benchmark_question_attempts_do_not_mix(harness: _Harness):
    """(2) Repeating one benchmark question keeps the two attempts separate."""
    scope_first = harness.scope(
        "apollo_hop_011",
        benchmark_id="apollo_multihop_50",
        question_id="apollo_hop_011",
    )
    scope_second = harness.scope(
        "apollo_hop_011",
        benchmark_id="apollo_multihop_50",
        question_id="apollo_hop_011",
    )
    harness.store.store_kgc_facts(scope_first, _apollo_facts())
    harness.store.store_kgc_facts(
        scope_second,
        _apollo_facts() + [KgcFact("Apollo 11", "launched_on", "July 16, 1969")],
    )

    first = harness.store.get_kgc_facts(scope_first.execution_id)
    second = harness.store.get_kgc_facts(scope_second.execution_id)
    assert len(first) == 2
    assert len(second) == 3
    assert all(
        record["question_id"] == "apollo_hop_011"
        for record in harness.store.get_fact_records(scope_first.execution_id)
    )


def test_fact_readback_scoped_to_requested_execution(harness: _Harness):
    """(3) FACT readback returns only the requested execution."""
    scope_a = harness.scope("readback_a")
    scope_b = harness.scope("readback_b")
    harness.store.store_kgc_facts(
        scope_a, [KgcFact("Alpha", "linked_to", "One", evidence="a")]
    )
    harness.store.store_kgc_facts(
        scope_b, [KgcFact("Beta", "linked_to", "Two", evidence="b")]
    )
    assert [f.object for f in harness.store.get_kgc_facts(scope_a.execution_id)] == ["One"]
    assert [f.object for f in harness.store.get_kgc_facts(scope_b.execution_id)] == ["Two"]


def _store_claims(store: Neo4jStore, scope: ExecutionScope) -> None:
    evaluations = [
        KgcEvaluationResult(
            triple=Triple("Neil Armstrong", "born_in", "Wapakoneta"),
            label=KgcClaimLabel.SUPPORTED,
            reason="match",
            evidence="ctx birth",
        ),
        KgcEvaluationResult(
            triple=Triple("Neil Armstrong", "born_in", "Cleveland"),
            label=KgcClaimLabel.CONTRADICTED,
            reason="conflict",
            evidence="ctx birth",
            conflicting_object="Wapakoneta",
        ),
        KgcEvaluationResult(
            triple=Triple("Neil Armstrong", "favorite_color", "blue"),
            label=KgcClaimLabel.NO_EVIDENCE,
            reason="missing",
            evidence="",
        ),
    ]
    store.store_kgc_claims(
        scope,
        iteration=0,
        evaluations=evaluations,
        answer_stage="sub_question_1_answer_0",
        sub_question_id=1,
    )


def test_claim_readback_scoped_to_requested_execution(harness: _Harness):
    """(4) CLAIM readback returns only the requested execution, object visible."""
    scope_a = harness.scope("claims_a")
    scope_b = harness.scope("claims_b")
    _store_claims(harness.store, scope_a)
    _store_claims(harness.store, scope_b)

    claims_a = harness.store.get_claims(scope_a.execution_id)
    assert len(claims_a) == 3
    assert all(c["execution_id"] == scope_a.execution_id for c in claims_a)
    # The object remains represented by the target node and stays visible.
    assert {c["object"] for c in claims_a} == {"Wapakoneta", "Cleveland", "blue"}
    assert all(c["sub_question_id"] == 1 for c in claims_a)


def test_bad_claims_include_no_evidence(harness: _Harness):
    """(5) NO_EVIDENCE is returned by the bad-claim query."""
    scope = harness.scope("bad_claims_noev")
    _store_claims(harness.store, scope)
    bad = harness.store.get_bad_claims(scope.execution_id)
    assert "NO_EVIDENCE" in {c["label"] for c in bad}


def test_bad_claims_include_contradicted(harness: _Harness):
    """(6) CONTRADICTED is returned by the bad-claim query; SUPPORTED is not."""
    scope = harness.scope("bad_claims_contra")
    _store_claims(harness.store, scope)
    bad = harness.store.get_bad_claims(scope.execution_id)
    labels = {c["label"] for c in bad}
    assert "CONTRADICTED" in labels
    assert "SUPPORTED" not in labels


def test_supported_claims_remain_claims(harness: _Harness):
    """(7) Supported CLAIMS never become FACT edges automatically."""
    scope = harness.scope("claims_stay_claims")
    harness.store.store_kgc_facts(scope, _apollo_facts())
    _store_claims(harness.store, scope)

    facts = {
        (f.subject, f.relation, f.object)
        for f in harness.store.get_kgc_facts(scope.execution_id)
    }
    assert len(facts) == 2
    # The supported claim triple exists as a FACT only because the trusted
    # context put it there, and the contradicted/no-evidence claim triples
    # must not appear as FACTs at all.
    assert ("Neil Armstrong", "born_in", "Cleveland") not in facts
    assert ("Neil Armstrong", "favorite_color", "blue") not in facts
    counts = harness.store.get_relationship_counts(scope.execution_id)
    assert counts["fact_edges"] == 2
    assert counts["claim_edges"] == 3


def test_focused_fact_provenance_roundtrip(harness: _Harness):
    """(8) Focused FACT provenance survives a Neo4j round-trip."""
    scope = harness.scope("focused_provenance")
    addition = WorkingKgcAddition(
        fact=KgcFact("Neil Armstrong", "born_in", "Wapakoneta", evidence="span"),
        provenance=KgcProvenanceType.TRUSTED_CONTEXT,
        extraction_scope="sub_question_focused",
        sub_question_id=2,
        evidence_spans=["Neil Armstrong was born in Wapakoneta."],
    )
    harness.store.store_working_kgc_additions(scope, [addition])
    records = harness.store.get_fact_records(scope.execution_id)
    assert len(records) == 1
    record = records[0]
    assert record["provenance"] == "trusted_context"
    assert record["extraction_stage"] == "sub_question_focused"
    assert record["sub_question_id"] == 2
    assert record["execution_id"] == scope.execution_id


def test_derived_fact_provenance_roundtrip(harness: _Harness):
    """(9) Derived FACT provenance survives a Neo4j round-trip."""
    scope = harness.scope("derived_provenance")
    addition = WorkingKgcAddition(
        fact=KgcFact("State Ohio", "contains", "Wapakoneta", evidence="derived span"),
        provenance=KgcProvenanceType.DERIVED_FROM_TRUSTED_CONTEXT,
        extraction_scope="target_fact_derivation",
        sub_question_id=3,
        derivation_type="containment_inference",
        evidence_spans=["Wapakoneta, Ohio"],
        derivation_explanation="Town-state containment stated in trusted context.",
    )
    harness.store.store_working_kgc_additions(scope, [addition])
    records = harness.store.get_fact_records(scope.execution_id)
    assert len(records) == 1
    record = records[0]
    assert record["provenance"] == "derived_from_trusted_context"
    assert record["derivation_type"] == "containment_inference"
    assert record["derivation_explanation"] == (
        "Town-state containment stated in trusted context."
    )
    assert record["extraction_stage"] == "target_fact_derivation"


def test_clearing_one_execution_leaves_another_intact(harness: _Harness):
    """(10) clear_execution removes one attempt and preserves the other."""
    scope_keep = harness.scope("clear_keep")
    scope_drop = harness.scope("clear_drop")
    harness.store.store_kgc_facts(scope_keep, _apollo_facts())
    harness.store.store_kgc_facts(scope_drop, _apollo_facts())
    _store_claims(harness.store, scope_drop)

    harness.store.clear_execution(scope_drop.execution_id)

    assert harness.store.get_kgc_facts(scope_drop.execution_id) == []
    assert harness.store.get_claims(scope_drop.execution_id) == []
    kept = harness.store.get_kgc_facts(scope_keep.execution_id)
    assert len(kept) == 2


def test_api_counts_match_direct_cypher(harness: _Harness):
    """(11) API-reported relationship counts equal direct Cypher counts."""
    scope = harness.scope("count_parity")
    harness.store.store_kgc_facts(scope, _apollo_facts())
    _store_claims(harness.store, scope)

    counts = harness.store.get_relationship_counts(scope.execution_id)
    with harness.store._session() as session:
        fact_direct = session.run(
            "MATCH ()-[r:FACT]->() WHERE r.execution_id = $x RETURN count(r) AS c",
            x=scope.execution_id,
        ).single()["c"]
        claim_direct = session.run(
            "MATCH ()-[r:CLAIM]->() WHERE r.execution_id = $x RETURN count(r) AS c",
            x=scope.execution_id,
        ).single()["c"]
    assert counts["fact_edges"] == int(fact_direct) == 2
    assert counts["claim_edges"] == int(claim_direct) == 3

    summary = harness.store.get_execution_summary(scope.execution_id)
    assert summary["fact_count"] == 2
    assert summary["claim_count"] == 3
    assert summary["claim_labels"].get("SUPPORTED") == 1
    assert summary["claim_labels"].get("CONTRADICTED") == 1
    assert summary["claim_labels"].get("NO_EVIDENCE") == 1


def test_neo4j_restart_preserves_named_volume_data(harness: _Harness):
    """(12) Restarting the container preserves data on the named volume."""
    container = os.getenv("NEO4J_CONTAINER", "grapheval-neo4j")
    if shutil.which("docker") is None:
        pytest.skip("docker CLI is required for the restart-persistence test")
    probe = subprocess.run(
        ["docker", "ps", "--filter", f"name=^{container}$", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if probe.returncode != 0 or container not in probe.stdout.split():
        pytest.skip(f"container {container} is not running under local docker")

    scope = harness.scope("restart_persistence")
    harness.store.store_kgc_facts(scope, _apollo_facts())
    harness.store.close()

    subprocess.run(
        ["docker", "restart", container],
        check=True,
        capture_output=True,
        timeout=180,
    )
    deadline = time.monotonic() + 120
    last_error: Exception | None = None
    store = None
    while time.monotonic() < deadline:
        try:
            store = Neo4jStore()
            store.verify_connectivity()
            facts = store.get_kgc_facts(scope.execution_id)
            if facts:
                break
            store.close()
            store = None
        except Exception as exc:  # Bolt not ready yet.
            last_error = exc
            if store is not None:
                store.close()
                store = None
        time.sleep(2)
    assert store is not None, f"Neo4j did not come back after restart: {last_error}"
    harness.store = store  # teardown cleans up through the fresh connection
    facts = store.get_kgc_facts(scope.execution_id)
    assert [(f.subject, f.relation, f.object) for f in facts] == [
        ("Apollo 11", "crewed_by", "Neil Armstrong"),
        ("Neil Armstrong", "born_in", "Wapakoneta"),
    ]


def test_neo4j_status_structure():
    if not _live_enabled():
        pytest.skip("Set GRAPHEVAL_LIVE_NEO4J=1")
    status = neo4j_status(required_for_this_route=True)
    assert "configured" in status
    assert "connected" in status
    assert "required_for_this_route" in status
    assert "error" in status
    assert "password" not in str(status).lower() or status.get("error")


def test_execution_id_shape():
    first = new_execution_id("apollo_hop_011")
    second = new_execution_id("apollo_hop_011")
    assert first != second
    assert first.startswith("apollo_hop_011__")
    parts = first.split("__")
    assert len(parts) == 3
    assert len(parts[2]) == 8
